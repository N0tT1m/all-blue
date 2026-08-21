"""FastAPI app.

Slice 1 endpoints:
  GET /content?q=          substring title search, paginated
  GET /content/{id}        one item plus its children
  GET /series/{id}/episodes  ordered correctly, across season boundaries
"""

from fastapi import FastAPI

app = FastAPI(title="All Blue")
