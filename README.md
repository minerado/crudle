# Crudle

**A CRUD library for SQLAlchemy models, plus an in-memory adapter for tests.**

Crudle extends your SQLAlchemy models with intuitive CRUD operations, advanced querying capabilities, and smart relationship handling. Reduce boilerplate code and build features more efficiently.

## Why Crudle?

- **Intuitive API**: Simple, readable methods
- **Powerful Querying**: Advanced filtering, sorting, and pagination
- **Smart Relationships**: Automatic handling of complex relationships and nested data
- **Flexible**: Custom filters and extensible architecture
- **In-memory twin**: `MemoryAdapter` for fast tests with Pydantic models

## Quick Start

### Basic Usage

```python
from crudle import SQLAlchemyAdapter
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Define your model
Base = declarative_base()

class User(Base, SQLAlchemyAdapter):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    email = Column(String(100))

# Setup database
engine = create_engine("sqlite:///example.db")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
db = Session()

# Start using Crudle
user = User.insert(db, name="John Doe", email="john@example.com")
users = User.list(db, name="John Doe")
user = User.get_by(db, email="john@example.com")
user.update(db, name="Jane Doe")
user.delete(db)
```

### Memory adapter (testing)

Same query dialect as SQLAlchemy (`field__op`, nested `.` paths, default `limit=25`,
`sort` / `skip` / `select` / `distinct_on`, `on_update_assocs`), with an instance-style API
for Pydantic models. Intended for tests and small local projects — not production storage.

**Memory-only differences:** no `commit` (ignored if passed), no custom `Queries` /
`search_fields`, and `q` is case-insensitive substring match (not Postgres FTS).

### Testing Postgres-only features (`q` FTS, `distinct_on`)

Default tests use SQLite. SQLAlchemy `q` / `search` FTS and `distinct_on`
tests are marked `@pytest.mark.postgres` and **skip** unless you opt in:

```bash
# Everyday (Memory suites + SQLite SQLAlchemy run; Postgres-only skipped)
pytest

# Opt-in Postgres (FTS + DISTINCT ON)
docker run --rm -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:16
CRUDLE_TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/postgres \
  pytest -m postgres
```

If port 5432 is already in use, map another host port (e.g. `-p 5433:5432`) and put that port in the URL.

The fixture creates extension `unaccent` and text search config `unaccent_simple`
(required by the SQLAlchemy `q` adapter). Postgres `distinct_on` lives in
`tests/crudle/adapters/sqlalchemy/list/test_list_distinct_on.py` (empty `[]` also
runs on SQLite). Memory’s in-process twin is
`tests/crudle/adapters/memory/test_list_distinct_on.py`.

```python
from pydantic import BaseModel
from crudle import MemoryAdapter

class Item(BaseModel):
    id: int | None = None
    name: str
    price: int | None = None

db = MemoryAdapter()
item = db.insert(Item, name="Widget", price=10)
items = db.list(Item, price__ge=5)
db.delete(Item, item.id)
```

## Core Features

### CRUD Operations

#### Create (Insert)

```python
# Simple insert
user = User.insert(db, name="Alice", email="alice@example.com")

# Insert with relationships
user = User.insert(db,
    name="Bob",
    department_id=1,
    role="developer"
)

# Insert with commit control
user = User.insert(db, name="Charlie", commit=False)
# ... do more operations
db.commit()  # Commit when ready
```

#### Read (Get & List)

```python
# Get by ID
user = User.get(db, 1)

# Get by criteria
user = User.get_by(db, email="alice@example.com")

# List with filters
users = User.list(db, age__gt=18, city="New York")

# List with pagination
users = User.list(db, limit=10, skip=20)

# List with sorting
users = User.list(db, sort=[
    {"field": "age", "order": "desc"},
    {"field": "name", "order": "asc"}
])
```

#### Update

```python
# Update instance
user.update(db, name="Alice Smith", age=31)

# Update by criteria
User.update_by(db, filters={"email": "alice@example.com"}, name="Alice Johnson")

# Update with relationship handling
user.update(db, role="senior_developer", department_id=2)
```

#### Delete

```python
# Delete instance
user.delete(db)

# Delete by criteria
User.delete_by(db, email="old@example.com")
```

### Advanced Querying

#### Filter Operators

```python
# Equality
users = User.list(db, status="active")

# Comparison operators
users = User.list(db,
    age__gt=18,                    # Greater than (integer)
    salary__ge=50000,             # Greater than or equal (decimal)
    created_at__lt=datetime.now(), # Less than (datetime)
    score__le=100,                # Less than or equal (float)
    name__ne="admin"              # Not equal (string)
)

# List operators
users = User.list(db,
    status__in=["active", "pending"],  # In list
    role__ni=["admin", "moderator"]    # Not in list
)

# Additional operators
users = User.list(db, name__ne="admin")  # Not equal
```

#### Complex Queries

```python
# Multiple filters
users = User.list(db,
    age__ge=18,
    city="New York",
    status__in=["active", "premium"],
    is_verified=True
)

# Nested relationship filters
posts = Post.list(db, **{"author.city": "San Francisco"})

# Deep nested filters
comments = Comment.list(db, **{"post.author.department": "Engineering"})

# Super complex nested filtering with multiple operators
complex_results = Comment.list(db,
    **{
        "post.author.department.name__in": ["Engineering", "Product"],
        "post.author.salary__ge": 80000,
        "post.tags.name__q": "python",
        "post.created_at__lt": datetime.now() - timedelta(days=30),
        "post.views__gt": 100,
        "author.profile.score__le": 95.5,
        "post.category.parent.name__ne": "archived"
    }
)
```

#### Field Selection & Query Options

```python
# Select specific fields
users = User.list(db, select=["name", "email", "age"])

# Select with relationships
users = User.list(db, select=["name", "profile.bio", "posts.title"])

# Return as dictionaries
users = User.list(db, return_dict=True)

# Count records
count = User.count(db, age__gt=18)
with_department = User.count(db, department__ne=None)
```

#### Sorting & Pagination

```python
# Single field sorting
users = User.list(db, sort=[{"field": "created_at", "order": "desc"}])

# Multiple field sorting
users = User.list(db, sort=[
    {"field": "department", "order": "asc"},
    {"field": "salary", "order": "desc"}
])

# Pagination
users = User.list(db, limit=20, skip=40)  # Page 3, 20 items per page
```

### Relationship Handling

#### One-to-One Relationships

```python
class User(Base, SQLAlchemyAdapter):
    # ... columns ...
    department = relationship("Department", back_populates="users")

class Department(Base, SQLAlchemyAdapter):
    # ... columns ...
    users = relationship("User", back_populates="department")

# Create with nested data
user = User.insert(db,
    name="John",
    department_id=1,
    role="developer"
)

# Query with relationship data
users = User.list(db, select=["name", "department.name"])
```

#### One-to-Many Relationships

```python
class User(Base, SQLAlchemyAdapter):
    # ... columns ...
    posts = relationship("Post", back_populates="author")

class Post(Base, SQLAlchemyAdapter):
    # ... columns ...
    author = relationship("User", back_populates="posts")

# Create with nested collections
user = User.insert(db,
    name="Alice",
    posts=[
        {"title": "My First Post", "content": "Hello world!"},
        {"title": "Second Post", "content": "Another post"}
    ]
)

# Query with relationship filters
users = User.list(db, **{"posts.title__q": "tutorial"})
```

#### Many-to-Many Relationships

```python
class User(Base, SQLAlchemyAdapter):
    # ... columns ...
    roles = relationship("Role", secondary="user_roles", back_populates="users")

class Role(Base, SQLAlchemyAdapter):
    # ... columns ...
    users = relationship("User", secondary="user_roles", back_populates="roles")

# Create with many-to-many
user = User.insert(db,
    name="Bob",
    roles=[
        {"name": "admin", "permissions": ["read", "write"]},
        {"name": "moderator", "permissions": ["read"]}
    ]
)
```

### Custom Filters

#### Custom Query Filters

```python
class User(Base, SQLAlchemyAdapter):
    # ... columns ...

    class Queries:
        def filter_is_adult(self, query, value):
            if value:
                return query.filter(User.age >= 18)
            return query.filter(User.age < 18)

        def filter_has_posts(self, query, value):
            if value:
                return query.filter(User.posts.any())
            return query.filter(~User.posts.any())

# Use custom filters
adults = User.list(db, is_adult=True)
active_users = User.list(db, has_posts=True)
```

**Note:** Custom filters are fully extensible and integrate seamlessly with SQLAlchemy. You can use any SQLAlchemy query methods, joins, subqueries, or complex expressions within your custom filter functions, giving you the full power of SQLAlchemy while maintaining Crudle's simple API.

### Field Selection & Query Options

#### Field Selection

```python
# Select specific fields
users = User.list(db, select=["id", "name", "email"])

# Select with relationships
users = User.list(db, select=["name", "department.name", "posts.title"])
```

#### Distinct Queries

```python
# Get unique values (PostgreSQL)
unique_cities = User.list(db, distinct_on=["city"])
unique_combinations = User.list(db, distinct_on=["department", "role"])
```

#### Upsert Operations

```python
# Update if exists, insert if not
user = User.upsert_by(db, {"email": "john@example.com"}, name="John Doe")
```

## Advanced Features

### Transaction Management

```python
# Control commits
user = User.insert(db, name="Test", commit=False)
# ... do more operations
db.commit()  # Commit all at once

# Update without committing
user = User.get(db, 1)
updated_user = user.update(db, name="New Name", commit=False)
# ... more operations
db.commit()
```

### Relationship Update Strategies

```python
# Different strategies for relationship updates
user = User.get(db, 1)

# Strategy 1: "raise" (default) - Raise error if conflicts exist
user.update(db,
    posts=[{"title": "New Post"}],
    on_update_assocs="raise"
)

# Strategy 2: "delete_all" - Delete all existing relationships and add new ones
user.update(db,
    posts=[{"title": "Post 1"}, {"title": "Post 2"}],
    on_update_assocs="delete_all"
)

# Strategy 3: "nilify_all" - Set foreign keys to NULL and add new relationships
user.update(db,
    department={"name": "New Department"},
    on_update_assocs="nilify_all"
)

# Strategy 4: Update with mixed existing and new relationships
user.update(db,
    posts=[
        {"id": 1, "title": "Updated Post"},  # Update existing
        {"title": "Brand New Post"}          # Create new
    ],
    on_update_assocs="delete_all"
)

# Strategy 5: Update many-to-many relationships
user.update(db,
    roles=[
        {"id": 1, "name": "admin"},          # Keep existing role
        {"name": "moderator"}                # Add new role
    ],
    on_update_assocs="delete_all"
)
```

## API Reference

### Class Methods

#### `insert(db, commit=True, **kwargs)`

Creates a new record with the provided attributes.

**Parameters:**

- `db`: SQLAlchemy session
- `commit`: Whether to commit the transaction (default: True)
- `**kwargs`: Model attributes and relationships

**Returns:** The created model instance

#### `get(db, id)`

Retrieves a record by its primary key.

**Parameters:**

- `db`: SQLAlchemy session
- `id`: Primary key value

**Returns:** Model instance or None

#### `get_by(db, **kwargs)`

Retrieves a record by specified filters.

**Parameters:**

- `db`: SQLAlchemy session
- `**kwargs`: Filter criteria

**Returns:** Model instance or None

#### `list(db, **kwargs)`

Lists records based on filters and options.

**Parameters:**

- `db`: SQLAlchemy session
- `limit`: Maximum number of records (default: 25)
- `skip`: Number of records to skip (default: 0)
- `sort`: List of sort specifications
- `select`: List of fields to select
- `return_dict`: Return dictionaries instead of model instances
- `distinct_on`: List of fields for distinct queries
- `**kwargs`: Filter criteria

**Returns:** List of model instances or dictionaries

#### `update_by(db, filters, should_raise=False, **kwargs)`

Updates records matching the filters.

**Parameters:**

- `db`: SQLAlchemy session
- `filters`: Dictionary of filter criteria
- `should_raise`: Whether to raise exception if no records found
- `**kwargs`: Attributes to update

**Returns:** Updated model instance or None

#### `delete_by(db, **kwargs)`

Deletes records matching the filters.

**Parameters:**

- `db`: SQLAlchemy session
- `**kwargs`: Filter criteria

**Returns:** Deleted model instance or None

#### `count(db, **kwargs)`

Counts records matching the filters. Shares the list filter / assoc /
``distinct_on`` dialect. Use ``field__ne=None`` for non-null scalars.
``limit`` / ``skip`` / ``sort`` / ``select`` / ``return_dict`` are ignored.

**Parameters:**

- `db`: SQLAlchemy session
- `**kwargs`: Filter criteria (and optional ``distinct_on``)

**Returns:** Integer count

#### `upsert_by(db, filters, **kwargs)`

Updates existing record or creates new one.

**Parameters:**

- `db`: SQLAlchemy session
- `filters`: Dictionary of filter criteria
- `**kwargs`: Attributes to set

**Returns:** Model instance

### Instance Methods

#### `update(db, on_update_assocs="raise", commit=True, **kwargs)`

Updates the current instance.

**Parameters:**

- `db`: SQLAlchemy session
- `on_update_assocs`: Strategy for relationship updates
- `commit`: Whether to commit the transaction
- `**kwargs`: Attributes to update

**Returns:** Updated model instance

#### `delete(db, commit=True)`

Deletes the current instance.

**Parameters:**

- `db`: SQLAlchemy session
- `commit`: Whether to commit the transaction

**Returns:** Deleted model instance

## Acknowledgments

- Built on top of [SQLAlchemy](https://www.sqlalchemy.org/) ORM
- Inspired by the simplicity of [Ecto](https://hexdocs.pm/ecto/Ecto.html) and [QueryElf](https://hexdocs.pm/query_elf/QueryElf.html)
- Powered by [Pydantic](https://pydantic.dev/) for data validation

---

**Made for developers who appreciate clean, readable code.**

_Happy coding!_
