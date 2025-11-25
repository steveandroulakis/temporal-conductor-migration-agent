# Streamlit UI Guide for Backend Integration

Streamlit is a Python framework for building interactive web applications with minimal code. Use it to add a UI layer to existing Python backends.

## Core Concepts

- Streamlit reruns the entire script on every user interaction
- Use `st.session_state` to persist data between reruns
- Use caching decorators to avoid recomputing expensive operations

## Display Functions

### Write and Display Data

```python
import streamlit as st
import pandas as pd

# Display text with markdown
st.write("# My App")
st.write("Some text here")

# Display dataframes as interactive tables
df = pd.DataFrame({'col1': [1, 2], 'col2': [3, 4]})
st.write(df)
st.dataframe(df)  # Full interactivity with sorting/filtering
```

### Stream LLM Responses

```python
import streamlit as st

def stream_data():
    for word in "Hello world".split():
        yield word + " "
        time.sleep(0.02)

st.write_stream(stream_data)

# Works directly with OpenAI streaming responses
# stream = client.chat.completions.create(..., stream=True)
# st.write_stream(stream)
```

## Interactive Widgets

### Common Widgets

```python
import streamlit as st

# Text input
name = st.text_input("Enter name")
description = st.text_area("Description")

# Selection
option = st.selectbox("Choose one", ["A", "B", "C"])
options = st.multiselect("Choose many", ["A", "B", "C"])

# Numeric
age = st.slider("Age", 0, 100, 25)
count = st.number_input("Count", min_value=0, max_value=100)

# Boolean
agree = st.checkbox("I agree")
enabled = st.toggle("Enable feature")

# Buttons
if st.button("Submit"):
    st.write("Submitted!")

# File upload
uploaded_file = st.file_uploader("Upload file", type=["csv", "txt"])
if uploaded_file:
    data = pd.read_csv(uploaded_file)
```

### Widget State

```python
# Widgets can use session_state for persistence
if "counter" not in st.session_state:
    st.session_state.counter = 0

if st.button("Increment"):
    st.session_state.counter += 1

st.write(f"Count: {st.session_state.counter}")

# Disable widgets conditionally
st.text_input("Name", disabled=st.session_state.get("locked", False))
```

## Data Visualization

```python
import streamlit as st
import pandas as pd

df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})

# Built-in charts
st.line_chart(df)
st.bar_chart(df)
st.area_chart(df)

# Maps (requires lat/lon columns)
st.map(data)

# Third-party charts work too
import plotly.express as px
fig = px.scatter(df, x="a", y="b")
st.plotly_chart(fig)
```

## Layout and Containers

```python
import streamlit as st

# Columns
col1, col2 = st.columns(2)
with col1:
    st.write("Left column")
with col2:
    st.write("Right column")

# Sidebar
with st.sidebar:
    st.write("Sidebar content")
    filter_option = st.selectbox("Filter", ["All", "Active"])

# Expander
with st.expander("Show details"):
    st.write("Hidden content here")

# Tabs
tab1, tab2 = st.tabs(["Tab 1", "Tab 2"])
with tab1:
    st.write("Tab 1 content")

# Empty placeholder for dynamic updates
placeholder = st.empty()
placeholder.write("Loading...")
# Later: placeholder.write("Done!")
```

## Caching for Backend Integration

### Cache Data Operations

```python
import streamlit as st

@st.cache_data
def fetch_data_from_backend(query_params):
    """Cached - won't rerun unless params change."""
    return backend.query(query_params)

@st.cache_data(ttl=300)  # Expires after 5 minutes
def fetch_live_data():
    return api.get_current_data()

# Exclude unhashable params with underscore prefix
@st.cache_data
def query_with_connection(_conn, sql):
    return _conn.execute(sql)

# Clear cache when needed
fetch_data_from_backend.clear()
st.cache_data.clear()  # Clear all
```

### Cache Resources (Singletons)

```python
import streamlit as st

@st.cache_resource
def get_database_connection():
    """Cached singleton - shared across all users/reruns."""
    return create_db_connection()

@st.cache_resource
def load_ml_model():
    return load_model("model.pkl")

conn = get_database_connection()
model = load_ml_model()
```

## Session State

```python
import streamlit as st

# Initialize state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Update state
st.session_state.messages.append({"role": "user", "content": "Hello"})

# Access state
for msg in st.session_state.messages:
    st.write(f"{msg['role']}: {msg['content']}")

# Use callbacks for widget state
def on_change():
    st.session_state.processed = True

st.text_input("Query", on_change=on_change, key="query_input")
```

## Multipage Apps

### Using pages/ Directory

```
your_app/
├── app.py              # Main entry point
└── pages/
    ├── 1_Dashboard.py
    ├── 2_Settings.py
```

### Programmatic Navigation

```python
import streamlit as st

page1 = st.Page("pages/home.py", title="Home", icon="🏠")
page2 = st.Page("pages/dashboard.py", title="Dashboard", icon="📊")

pg = st.navigation([page1, page2])
pg.run()

# Switch pages programmatically
if st.button("Go to Dashboard"):
    st.switch_page("pages/dashboard.py")
```

## Database Connections

```python
import streamlit as st

# Built-in SQL connection with caching
conn = st.connection("postgresql", type="sql")
df = conn.query("SELECT * FROM users", ttl=600)

# Or use your existing backend connection
@st.cache_resource
def get_backend():
    from mybackend import Backend
    return Backend()

backend = get_backend()
data = backend.fetch_users()
st.dataframe(data)
```

## Status and Feedback

```python
import streamlit as st

# Messages
st.success("Operation completed!")
st.error("Something went wrong")
st.warning("Be careful")
st.info("FYI")

# Progress
progress = st.progress(0)
for i in range(100):
    progress.progress(i + 1)

# Spinner
with st.spinner("Processing..."):
    result = slow_operation()

# Toast notifications
st.toast("Saved!", icon="✅")
```

## Running the App

```bash
# Basic run
streamlit run app.py

# Custom port
streamlit run app.py --server.port 8080

# Clear cache
streamlit cache clear
```

## Configuration

Create `.streamlit/config.toml`:

```toml
[server]
port = 8501
maxUploadSize = 200

[theme]
primaryColor = "#F63366"
backgroundColor = "#FFFFFF"
```

## Integration Pattern Example

```python
# app.py - Adding UI to existing backend
import streamlit as st
from mybackend import Backend, process_data

@st.cache_resource
def get_backend():
    return Backend()

def main():
    st.title("My Backend UI")
    backend = get_backend()

    # Sidebar for inputs
    with st.sidebar:
        query = st.text_input("Search")
        filters = st.multiselect("Filters", backend.get_filter_options())

    # Main content
    if query:
        with st.spinner("Searching..."):
            results = backend.search(query, filters)

        if results:
            st.dataframe(results)

            if st.button("Process Selected"):
                processed = process_data(results)
                st.success(f"Processed {len(processed)} items")
        else:
            st.info("No results found")

if __name__ == "__main__":
    main()
```
