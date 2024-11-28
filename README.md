# Assignment 1: Network Application Development

This project is a major assignment for the Computer Networks course, Semester 241, at Ho Chi Minh City University of Technology.

## Team Members
- **Lê Văn Anh Khoa** - 2211605
- **Võ Thanh Tâm** - 2213046

## Getting Started

### Prerequisites

To set up the project environment, please install the required libraries by running:
```bash
pip install -r requirements.txt
```

## Running the application
### 1. Start the tracker server by executing:
```bash
python TrackerServer.py
```
### 2. Launch the main application with:
```bash
python app.py
```
Alternatively, you can run the application in command-line mode with:
```bash
python main.py
```
This way requires manually path input (for choosing torrent, and for choosing download location)
## Features
- Share and download file or folder (contains many files) via .torrent file
- Get scrape info about any .torrent file
## Notes
Currently the app can only run on localhost, or between peer within a machine with TrackerServer hosted in another machine. The reason are firewall rules, haven't figured out how to bypass them to make peers from different networks can communicate.
