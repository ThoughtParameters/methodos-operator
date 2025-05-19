import os
import shutil
import tarfile
import json
import asyncio
import aiofiles
import hashlib
import datetime

from pathlib import Path as PyPath


from fastapi import APIRouter, HTTPException, status, UploadFile, File, Path, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from pydantic import ValidationError
from typing import List, Any, Dict

try:
  from app import logger 

  from app import TMP_DIR, INDEX_FILE, BOOKS_DIR
  from app import calculate_dir_checksum, calculate_sha256
  from app.models.books import Metadata, IndexEntry
  from app.responses.books import UploadResponse
except ImportError as e:
  print(f"Error importing modules: {e}")
  raise

book_index: Dict[str, Dict[str, Any]] = {}
index_lock = asyncio.Lock()

try:
  _TMP_DIR_PATH: PyPath = PyPath(TMP_DIR).resolve(strict=False)
  _BOOKS_DIR_PATH: PyPath = PyPath(BOOKS_DIR).resolve(strict=False)
  _INDEX_FILE_PATH: PyPath = PyPath(INDEX_FILE).resolve(strict=False)
except Exception as e:
  logger.critical(f"Critical error resolving directory paths (TMP_DIR, BOOKS_DIR, INDEX_FILE): {e}")
  raise

books_router = APIRouter(
  prefix='/books',
  tags=["Books"],
  responses={
    status.HTTP_400_BAD_REQUEST: {"description": "Bad Request - Invalid input, file structure, or validation error."},
    status.HTTP_404_NOT_FOUND: {"description": "Not Found - The requested resource does not exist."},
    status.HTTP_409_CONFLICT: {"description": "Conflict - The resource (e.g., book) already exists."},
    status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal Server Error - An unexpected error occurred on the server."},
  },
)

# --- Helper Functions ---
def _is_within_directory(directory: PyPath, target: PyPath) -> bool:
  """
  Safely checks if the target path is within the specified directory.
  Resolves symbolic links to prevent path traversal.
  """
  abs_directory = directory.resolve()
  abs_target = target.resolve() # Resolves target path fully
  return abs_directory in abs_target.parents or abs_directory == abs_target

async def _cleanup_temp_paths(paths_to_remove: List[PyPath]):
    """
    Asynchronously cleans up specified temporary files and directories.
    Intended for use in BackgroundTasks.
    """
    for path_to_remove in paths_to_remove:
        try:
            if await asyncio.to_thread(path_to_remove.exists):
                if await asyncio.to_thread(path_to_remove.is_dir):
                    logger.info(f"Background cleanup: Removing temporary directory {path_to_remove}")
                    await asyncio.to_thread(shutil.rmtree, path_to_remove)
                else:
                    logger.info(f"Background cleanup: Removing temporary file {path_to_remove}")
                    await asyncio.to_thread(os.remove, path_to_remove)
        except Exception as e:
            logger.error(f"Error during background cleanup of {path_to_remove}: {e}", exc_info=True)

async def load_index():
  """Loads the index from the JSON file."""
  global book_index
  async with index_lock:
    if os.path.exists(_INDEX_FILE_PATH):
      try:
        async with aiofiles.open(_INDEX_FILE_PATH, mode='r') as f:
          content = await f.read()
          book_index = json.loads(content)
      except (json.JSONDecodeError, IOError) as e:
        logger.critical(f"Error loading index file: {e}. Starting with empty index.")
        book_index = {}
    else:
      book_index = {}
  
  logger.info(f"Index loaded with {len(book_index)} entries.")

async def save_index():
  """Saves the current index to the JSON file."""
  async with index_lock:
    try:
      async with aiofiles.open(_INDEX_FILE_PATH, mode="w") as f:
         await f.write(json.dumps(book_index, indent=2))
    except IOError as e:
      logger.critical(f"Error saving index file: {e}.")

  logger.info(f"Index saved with {len(book_index)} entries.")
async def _extract_and_validate_tar(
    temp_tar_path: PyPath, temp_extract_path: PyPath
) -> Metadata:
  """
  Extracts the tarball and validates its contents against the Metadata model
  and checksums. Returns the validated Metadata object.
  Raises HTTPException on failure.
  """
  await asyncio.to_thread(temp_extract_path.mkdir, parents=True, exist_ok=True)

  try:
    # Perform synchronous tar operations in a thread pool
    def blocking_tar_operations():
      nonlocal metadata_obj
      has_metadata_file_in_tar = False
      has_chapters_content_in_tar = False

      with tarfile.open(temp_tar_path, 'r:gz') as tar:
        # Check for required files/dirs by inspecting members
        tar_members = tar.getmembers()
        member_names = [member.name for member in tar_members]

        if "metadata.json" not in member_names:
          raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid package: 'metadata.json' missing.")
              
        # Check if 'chapters/' exists and is a directory or contains files
        is_chapters_dir_present = any(m.name == "chapters" and m.isdir() for m in tar_members)
        has_files_in_chapters = any(m.name.startswith("chapters/") and m.isfile() for m in tar_members)

        if not (is_chapters_dir_present or has_files_in_chapters): # chapters/ can be empty but must exist, or contain files
          raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid package: 'chapters/' directory or its content is missing.")

        # Safe extraction
        for member in tar_members:
          member_destination_path = temp_extract_path / member.name
          if not _is_within_directory(temp_extract_path, member_destination_path):
            logger.error(f"Path traversal attempt detected in tar member: {member.name}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid package: Path traversal detected.")

          if member.name == "metadata.json":
            has_metadata_file_in_tar = True
          if member.name.startswith("chapters/") and member.isfile(): # Ensure there's content
            has_chapters_content_in_tar = True

          if member.isdir():
            # Create directories explicitly; extract skips some empty ones or handles perms oddly
            member_destination_path.mkdir(parents=True, exist_ok=True)
          elif member.isfile():
            # Ensure parent directory exists before extracting file
            member_destination_path.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(member) as source, open(member_destination_path, 'wb') as target:
              shutil.copyfileobj(source, target)
          else:
            logger.warning(f"Skipping non-file/non-dir tar member: {member.name} (type: {member.type})")
              
          if not has_metadata_file_in_tar: # Should be caught earlier
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid package: 'metadata.json' failed to extract.")

          metadata_file_path = temp_extract_path / "metadata.json"
          
          with open(metadata_file_path, 'r') as f:
            metadata_data = json.load(f)
              
          validated_metadata = Metadata(**metadata_data)
          return validated_metadata # Return from the synchronous function

    metadata_obj = await asyncio.to_thread(blocking_tar_operations)

      # Validate metadata (already done by Pydantic in blocking_tar_operations)
      # Validate chapters directory and checksum
    chapters_dir_actual_path = temp_extract_path / "chapters"
    if not await asyncio.to_thread(chapters_dir_actual_path.is_dir):
      # This confirms 'chapters' is a directory on disk post-extraction
      raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid package: 'chapters/' is not a directory after extraction.")

    # Assuming caculate_dir_checksum is a synchronous, potentially blocking function
    calculated_chapters_checksum = await asyncio.to_thread(
      calculate_dir_checksum, chapters_dir_actual_path, metadata_obj.checksum_algorithm
    )

    if calculated_chapters_checksum != metadata_obj.checksum:
      logger.warning(f"Checksum mismatch for {metadata_obj.name} v{metadata_obj.version}. Expected: {metadata_obj.checksum}, Got: {calculated_chapters_checksum}")
      raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Content checksum mismatch. The file may be corrupted or tampered with.")

    return metadata_obj

  except tarfile.TarError as e:
      logger.error(f"TarError during extraction for {temp_tar_path.name}: {e}", exc_info=True)
      raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid or corrupted book file: {e}")
  except ValidationError as e: # Pydantic validation error
      logger.warning(f"Metadata validation failed for {temp_tar_path.name}: {e.errors()}", exc_info=True)
      raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid metadata: {e.errors()}")
  except FileNotFoundError as e:
      logger.error(f"FileNotFoundError during extraction of {temp_tar_path.name}: {e}", exc_info=True)
      raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing expected file during processing: {e.filename}")
  except HTTPException: # Re-raise our own specific HTTP exceptions
      raise
  except Exception as e: # Catch any other unexpected errors
      logger.error(f"Unexpected error during package processing for {temp_tar_path.name}: {e}", exc_info=True)
      raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while processing the package.")

# --- Startup Events ---
@books_router.on_event("startup")
async def startup_event():
  """Ensure necessary directories exist at application startup."""
  logger.info("Application startup: Ensuring directories exist.")
  await asyncio.to_thread(_TMP_DIR_PATH.mkdir, parents=True, exist_ok=True)
  await asyncio.to_thread(_BOOKS_DIR_PATH.mkdir, parents=True, exist_ok=True)
  # You might also load the index from _INDEX_FILE_PATH here if it's not already loaded.


# --- Upload Book Endpoint ---
# This endpoint allows users to upload a book package (.book or .tar.gz) to the server.
# The package must contain a metadata.json file and a chapters/ directory.
# The metadata.json file must conform to the Metadata model defined in app/models/books.py.
# The chapters/ directory must contain the book's content.
# The endpoint validates the package structure, extracts the contents, and calculates checksums.
# It also checks for path traversal vulnerabilities during extraction.
# The uploaded book is stored in the BOOKS_DIR directory, and an index entry is created for it.
# The index is saved to disk asynchronously.
@books_router.post(
  path='/upload',
  status_code=status.HTTP_201_CREATED,
)

async def upload_book(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Book file to upload"),
):
  """
  Uploads a book to the server.
  """
  if not file.filename.endswith('.book') and not file.filename.endswith('.tar.gz'):
    raise HTTPException(status_code=400, detail="Invalid file type. Only .book and .tar.gz files are allowed.")
  
  temp_tar_path = os.path.join(TMP_DIR, f"upload_{file.filename}")
  temp_extract_path = os.path.join(TMP_DIR, f"extract_{file.filename}")

  def cleanup_temp(paths_to_remove: List[str]):
    for path in paths_to_remove:
      if os.path.exists(path):
        if os.path.isdir(path):
          shutil.rmtree(path)
        else:
          os.remove(path)
    print(f"Cleaned up temporary files: {paths_to_remove}")

  # Ensure cleanup runs even if errors occur mid-processing
  background_tasks.add_task(cleanup_temp, [temp_tar_path, temp_extract_path])

    # --- Save Uploaded File Temporarily ---
  try:
    async with aiofiles.open(temp_tar_path, 'wb') as out_file:
      while content := await file.read(1024 * 1024):
        await out_file.write(content)
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error saving file: {e}")
  finally:
    await file.close()

  # -- Extract and Validate ---
  metadata_dict = None
  caculate_code_checksum = None
  try:
    with tarfile.open(temp_tar_path, 'r:gz') as tar:
      for members in tar.getnames():
        if "metadata.json" not in members:
          raise HTTPException(status_code=400, detail="Invalid file structure, 'metadata.json' file is required.")
        elif not any(m.startswith("chapters/") for m in members):
          raise HTTPException(status_code=400, detail="Invalid file structure, 'chapters/' directory is required.")
          caculate_code_checksum = caculate_dir_checksum(os.path.join(temp_extract_path, member.name))

      # Extract safely
      # Warning: tarfile extraction can be vulnerable if paths are absolute or contain '..'
      # A productoin system might need more robust path checking/santiziation here.
      def is_with_directory(directory, target):
        abs_directory = os.path.abspath(directory)
        abs_target = os.path.abspath(target)
        prefix = os.path.commonprefix([abs_directory, abs_target])
        return prefix == abs_directory

      for member in tar.getmembers():
        member_path = os.path.join(temp_extract_path, member.name)
        # Prevent path traverals vulnerabilities
        if not is_with_directory(temp_extract_path, member_path):
          raise HTTPException(status_code=400, detail="Invalid file structure, path traversal detected.")

        if member.isfile():
          tar.extract(member, path=temp_extract_path, set_attrs=False)
        elif member.isdir():
          tar.extract(member, path=temp_extract_path, set_attrs=False)
        # Ignore other types like symlinks for simplicity/security here

      # Read metadata
      metadata_path = os.path.join(temp_extract_path, "metadata.json")
      if not os.path.exists(metadata_path):
        raise HTTPException(status_code=400, detail="Invalid file structure, 'metadata.json' file is required.")
      
      with open(metadata_path, 'r') as f:
        metadata_dict = json.load(f)

      # Validate metadata structure
      try:
        metadata = Metadata(**metadata_dict)
      except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Invalid metadata structure in 'metadata.json': {e}")
      
      # Calculate checksum
      chapters_dir_path = os.path.join(temp_extract_path, "chapters")
      if not os.path.isdir(chapters_dir_path):
        raise HTTPException(status_code=400, detail="Invalid file structure, 'chapters/' directory is required.")
      
      caculated_code_checksum = caculate_dir_checksum(chapters_dir_path, metadata.checksum_algorithm)

      # Verify code checksum
      if caculated_code_checksum != metadata.checksum:
        raise HTTPException(status_code=400, detail="Checksum mismatch. The file may be corrupted or tampered with.")
  
  except tarfile.TarError as e:
    raise HTTPException(status_code=400, detail=f"Invalid or corrupted book file: {e}")
  except FileNotFoundError as e:
    raise HTTPException(status_code=400, detail=f"Missing expected file during extraction/validation: {e}")
  except HTTPException: # Re-raise HTTP exceptions
    raise
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error processing package: {e}")
  finally:
    # Cleanup temporary files
    if os.path.exists(temp_extract_path):
      try:
        shutil.rmtree(temp_extract_path)
      except Exception as e:
        print(f"Error cleaning up extracted files: {e}")

    # Cleanup temporary tar file
    if os.path.exists(temp_tar_path):
      try:
        os.remove(temp_tar_path)
      except Exception as e:
        print(f"Error cleaning up temporary tar file: {e}")

  # --- Process Valid Book ---
  book_name = metadata.name
  book_version = metadata.version
  book_key = f"{book_name}-{book_version}"

  # Calculate checksum of the *entire* uploaded .book file for download verification
  book_checksum = caculate_sha256(temp_tar_path)
  final_book_filename = f"{book_key}.book"
  final_book_path = os.path.join(BOOKS_DIR, final_book_filename)

  # Add server-side metadata
  index_entry = metadata.model_dump() # Get dict from Pydantic model
  index_entry["book_filename"] = final_book_filename
  index_entry["book_checksum_algo"] = "sha256"
  index_entry["book_checksum"] = book_checksum
  index_entry["book_upload_timestamp"] = datetime.datetime.now().isoformat()

  async with index_lock:
    # Check if book already exists
    if book_key in book_index:
      # Decide on overwrite behavior - here we prevent it
      raise HTTPException(status_code=400, detail="Book already exists.")
    
    # Move validated package to final destination
    try:
      shutil.move(temp_tar_path, final_book_path)
    except Exception as e:
      raise HTTPException(status_code=500, detail=f"Failed to store book file: {e}")
    
    # Update index in memory
    book_index[book_key] = index_entry

    # Save index to disk asynchronously
    await save_index()

  return JSONResponse(content={
    "message": "Book uploaded and indexed successfully.",
    "book_key": book_key,
    "book_filename": final_book_filename,
    "book_checksum": book_checksum,
  }, status_code=status.HTTP_201_CREATED)

@books_router.get("/index", response_model=Dict[str, Dict[str, Any]])
async def get_book_index():
  """
  Returns the current book index.
  """
  async with index_lock:
    return JSONResponse(content=book_index, status_code=200)