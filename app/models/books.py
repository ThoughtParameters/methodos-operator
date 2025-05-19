from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

import datetime

from app.enums.books import Architecture, Platform

class Dependency(BaseModel):
  name: str = Field(..., description="Name of the dependency")
  version: str = Field(..., description="Version of the dependency")

class Metadata(BaseModel):
  name: str = Field(..., description="Name of the book")
  version: str = Field(..., description="Version of the book")
  description: str = Field(..., description="Description of the book")
  checksum_algorithm: str = Field(..., pattern="^sha256$|^sha512$|^md5$", description="Checksum algorithm used")
  checksum: str = Field(..., description="Checksum of the book")
  author: Optional[str] = Field(..., description="Author of the book")
  dependencies: Optional[List[Dependency]] = Field(None, description="List of dependencies for the book")
  tags: Optional[List[str]] = Field(None, description="List of tags for the book")
  license: Optional[str] = Field(None, description="License of the book")
  supported_architectures: List[Architecture] = Field(..., description="List of supported architectures for the book")
  supported_platforms: List[Platform] = Field(..., description="List of supported operating systems for the book")
  variables: Optional[Dict[str, Any]] = Field(None, description="List of variables for the book")

class IndexEntry(Metadata):
  """
  Represents a book's entry in the index, extending the user-provided metadata
  with server-side information.
  """
  book_filename: str = Field(..., description="The filename of the book package on the server.")
  book_checksum_algo: str = Field(default="sha256", description="Algorithm used for the book package checksum.")
  book_checksum: str = Field(..., description="Checksum of the entire book package (.book file).")
  book_upload_timestamp: datetime.datetime = Field(..., description="UTC timestamp of when the book was uploaded.")
