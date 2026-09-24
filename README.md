*This project has been created as part of the 42 curriculum by nfalkens and jihchoi.*

# A-MAZE-ING (2026)

## Description

In this project we created a maze generator and solver written in python.
The user can generate a maze of a customizable size. 
Graphics will be visualized in the terminal using a display loop and coloring via ANSI escape codes.

## Instructions

### Requirements

- Python >= 3.10
- linters (flake8, mypy) will be installed in the next step

### Installation

1. **Clone repository**

Vogsphere repo:
```bash
git clone git@vogsphere.42heilbronn.de:vogsphere/intra-uuid-1511a690-ff8d-4361-aa79-91a1a1fa9ae6-7569926-nfalkens
```
or

GitHub repo:
```bash
git clone git@github.com:Jihoon0303/A-Maze-ing.git
```

2. **create and activate venv**
```bash
python -m venv venv
```
```bash
source venv/bin/activate
```
3. **install requirements (flake8, mypy)**
```bash
make install
```
4. **Run common tasks**
```bash
make run    # runs the program
make lint   # lint and type checker
make debug  # run with debugger
make clean  # remove temporary files
```
5. **Exit venv when done**
```bash
deactivate
```

## Config File

The config file (example: config.txt) lets you change the maze setting:
```
WIDTH=20               # width of the maze 
HEIGHT=15              # height of the maze
ENTRY=0,0		       # Coords of entry
EXIT=19,14             # Coords of exit
OUTPUT_FILE=maze.txt   # path to save the output file
PERFECT=False          # perfect or non perfect maze
```

## Algorithms used

* **Algorithm:** BFS
* **Reason for choice:** Simple implementation, effiecient for small projects requiring fill control over a mazegen.

## Reusability

Different parts of **mazegen** and **output/display** are reusable and dont depent on each other necessarily.

## Project management in the team

### Roles

* **jihchoi:** mazegen, algorithms, solver, packaging
* **nfalkens:** config parsing, display loop, hex output, readme

### Planning

We had highly ambitious plans but sticked to simpler solutions for clean handling and output.

### Future Improvements

Display loop currently shows multiple instances of previously created mazes in the terminal. To improve this we want to show one instance per loop iteration.

## Resources
* Python official documentation
* [Packaging guide](https://packaging.python.org/en/latest/tutorials/packaging-projects/)
* [Algorithm references for BFS](https://en.wikipedia.org/wiki/Breadth-first_search)
* AI was used for code organization and file structuring
