# DataLoader

A Python package for efficiently loading and querying data from ClickHouse databases with a clean, intuitive API.

## Installation

### Prerequisites

1. **Create a GitHub Personal Access Token (Classic)**
   - Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Click "Generate new token (classic)"
   - Give it a descriptive name (e.g., "DataLoader Package Access")
   - Select the `repo` scope (this grants full control of private repositories)
   - Click "Generate token"

2. **Install the package**

```bash
pip install git+https://<PAT>@github.com/SSMIF-Quant/dataloader.git@main
```

Replace `<PAT>` with your Personal Access Token.

**Example:**
```bash
pip install git+https://ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx@github.com/SSMIF-Quant/dataloader.git@main
```

## Code Structure

### Core Components

```
dataloader/
├── __init__.py          # Package initialization
├── _client.py           # ClickHouse client wrapper
├── _manager.py          # Connection manager
├── _env.py              # Environment configuration
├── _pool.py             # Connection pooling
└── loader.py            # Main DataLoader class
```

### Key Classes

- **`DataLoader`**: Main interface for querying data
- **`Client`**: Handles ClickHouse queries and connections
- **`Manager`**: Manages database connections and pooling
- **`ConnectionPool`**: Maintains reusable database connections

## DataLoader Methods

### `query()`

Fetch data from ClickHouse with flexible filtering and column selection.

**Parameters:**
- `source` (str): Table or materialized view name
- `columns_list` (Optional[List[str]]): Explicit list of columns to select
- `column_pattern` (Optional[List[str]]): Pattern-based column selection (e.g., `["IS_*"]` for all columns starting with "IS_")
- `filters` (Optional[Dict[str, Any]]): Key-value pairs for WHERE clause filtering
- `limit` (Optional[int]): Maximum number of rows to return
- `offset` (Optional[int]): Number of rows to skip

**Returns:** `pd.DataFrame` with `Date` as index (sorted and deduplicated)

### `tables()`

List all available tables in the database.

**Returns:** `List[str]` of table names

### `fields()`

Get all columns for a specific table.

**Parameters:**
- `source` (str): Table or view name

**Returns:** `List[str]` of column names

## Usage Examples

### Example 1: Load Equity Data with Column Patterns

```python
from dataloader import DataLoader

# Get all income statement columns for Apple
equities_data = DataLoader.query(
    source="equities",
    column_pattern=["IS_*"],  # All columns starting with "IS_"
    filters={"symbol": "AAPL"}
)

print(equities_data.head())
```

### Example 2: Load Macro Data with Specific Columns

```python
from dataloader import DataLoader

# Get specific macro indicators
macro_data = DataLoader.query(
    source="macro",
    columns_list=["XLB", "THREEFYTP10", "DSWP10", "DGS10", "BAMLEMHBHYCRPIOAS", "T10Y2Y"]
)

print(macro_data.info())
```

### Example 3: Multiple Filters and Limits

```python
from dataloader import DataLoader

# Get data for multiple symbols with limit
multi_symbol_data = DataLoader.query(
    source="equities",
    columns_list=["PX_LAST", "CUR_MKT_CAP", "PX_VOLUME"],
    filters={
        "symbol": ["AAPL", "GOOGL", "MSFT"]
    },
    limit=1000
)

print(multi_symbol_data)
```

### Example 4: Discover Available Data

```python
from dataloader import DataLoader

# List all available tables
tables = DataLoader.tables()
print("Available tables:", tables)

# Get columns for a specific table
equity_columns = DataLoader.fields("equities")
print("Equity columns:", equity_columns)

macro_columns = DataLoader.fields("macro")
print("Macro columns:", macro_columns)
```

### Example 5: Combining Column Selection Methods

```python
from dataloader import DataLoader

# Mix explicit columns and patterns
combined_data = DataLoader.query(
    source="equities",
    columns_list=["PX_LAST"],  # Explicit columns
    column_pattern=["IS_*", "BS_*"],  # Income Statement + Balance Sheet columns
    filters={"symbol": "TSLA"}
)

print(combined_data.columns.tolist())
```

### Example 6: Pagination

```python
from dataloader import DataLoader

# Get data in chunks
page_1 = DataLoader.query(
    source="equities",
    columns_list=["PX_LAST"],
    filters={"symbol": "AAPL"},
    limit=100,
    offset=0
)

page_2 = DataLoader.query(
    source="equities",
    columns_list=["PX_LAST"],
    filters={"symbol": "AAPL"},
    limit=100,
    offset=100
)

print(f"Page 1: {len(page_1)} rows")
print(f"Page 2: {len(page_2)} rows")
```

## Features

✅ **Dynamic Column Selection**: Use patterns to select multiple columns at once  
✅ **Flexible Filtering**: Support for single values and lists  
✅ **Automatic Date Handling**: Returns DataFrame with Date index  
✅ **Deduplication**: Automatically removes duplicate dates  
✅ **Connection Pooling**: Efficient database connection management  

## Output Format

All queries return a `pandas.DataFrame` with:
- `Date` column as the index (datetime type)
- Sorted by date (ascending)
- Duplicates removed based on date
- All selected columns as specified

## Notes

- The `date` column is automatically included in all queries
- The `symbol` column is included when filtering by multiple symbols
- The columns are renamed for clarity when filtering by a single symbol
- Dates are converted to pandas datetime objects
- Results are always sorted by date
- The default database is `ssmif_quant`
- Connection credentials are managed via environment variables

## Support

For issues or questions, please contact the SSMIF Quant team or open an issue in the repository.
