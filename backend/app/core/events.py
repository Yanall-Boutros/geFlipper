# Process-wide signals between background tasks
import asyncio

# Set by the GE price collector after it commits a new Jagex update.
# The indicator engine waits on it so indicators follow new data immediately.
price_data_updated = asyncio.Event()
