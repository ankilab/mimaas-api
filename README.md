# MIMaaS Python SDK

Python client library for the MIMaaS (Microcontroller Model as a Service) API. Submit TensorFlow Lite models, benchmark them on real microcontroller hardware, and get back detailed performance metrics.

## Installation

First, clone this repository onto your local machine. Then:

```bash
pip install -e .
```

<!-- With power analysis visualization:

```bash
pip install -e ".[viz]"
``` -->

## Quick Start

Please have a look at the notebook provided in this repo to see how to use MIMAAS inside of your code environment.

Otherwise, you can always use the API directly in the IDE of your choice. 

```python
from mimaas import MIMaaSClient

client = MIMaaSClient()
client.login("your_username", "your_password")

# Submit a model for evaluation
request = client.submit_request("yourmodel.tflite", "nrf5340dk")

# Wait for results
results = client.wait_for_completion(request.id)
print(results)
```

**Output:**

```
Results:
  Inference Time: 12.34 ms
  Energy: 45.67 µJ
  Power: 3702.10 µW
  RAM: 48.2 KB
  Flash: 112.5 KB
```


## Usage

### Account Management

```python
# Register a new account (invite_token is a single-use token from an admin)
# Registration requires a single-use invite token from an admin.
api_token = client.register(
    username="my_username",
    email="my_email@provider.com",
    first_name="Myname",
    surname="Mysurname",
    password="MySecretPassword1!",  # Pwd needs Capital letters, special characters and a number
    invite_token="my_token",
)

# Check your profile and remaining runs
profile = client.get_profile()
print(f"Runs remaining: {profile.available_runs}")


```

### Browse Available Boards

```python
boards = client.list_boards()
for board in boards:
    print(board)  # specs + live status and queue length

# How busy is each board type? Requests are queued per type,
# and the next free board of that type runs them.
client.board_utilization()
# Board type          Online  Idle  Busy  Queued
# nrf5340dk              2/2     0     2       3

# Check a specific board
board = client.get_board("nrf5340dk")
status = client.get_board_status("nrf5340dk")
```

### Submit and See Requests

```python
# Validate before submitting (does not consume a run)
result = client.validate_model("model.tflite", "nrf5340dk")

# Submit for evaluation
request = client.submit_request("model.tflite", "nrf5340dk", quantize=False)

# Poll manually
req = client.get_request(request.id)
print(req.status)  # "pending" | "processing" | "done" | "error"
print(req.queue_position)  # 1 = next in line; None once it's running

# Or block until done (prints status changes and queue position; verbose=False to silence)
results = client.wait_for_completion(request.id, timeout=600)
# [   0.0s] Request #42: pending — position 3 in queue for nrf5340dk, 2/2 boards busy
# [  61.8s] Request #42: processing

# List past requests
all_requests = client.list_requests()
done = client.list_requests(status="done", board="nrf5340dk")
```

### Download Artifacts

```python
client.download_ram_report(request.id, "ram.json")
client.download_rom_report(request.id, "rom.json")
client.download_power_summary(request.id, "ppk2_summary.csv")
client.download_power_samples(request.id, "ppk2_samples.csv")
client.download_model(request.id, "model.tflite")

# Or grab everything at once
client.download_all_artifacts(request.id, "artifacts.zip")
```

### Power Analysis Visualization

<!-- Requires the `viz` extra (`pip install -e ".[viz]"`). -->

```python
from mimaas.viz import plot_power_analysis

fig = plot_power_analysis("ppk2_samples.csv")
fig.show()
```

Generates a simple, interactive dashboard with current draw over time. Intended for inital visualization of the results.