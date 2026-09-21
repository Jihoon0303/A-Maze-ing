import sys
from config import ConfigError, parse_config
from output import OutputError, write_output, path_to_directions
from mazegen.maze_generator import MazeGenerator
from mazegen.maze import Maze
from mazegen.maze_solver import MazeSolver


def main() -> None:
    """
    Creates config instance and catches Usage errors
    Generates maze and creates hex output file from it
    """
    if len(sys.argv) != 2:
        print(f"Usage: python3 {sys.argv[0]} <config_file>")
        sys.exit(1)
    try:
        config = parse_config(sys.argv[1])
    except ConfigError as e:
        print(f"Error: {e}")
        sys.exit(1)
    # placeholders:
    maze = Maze(config.width, config.height)
    MazeGenerator(maze).generate()
    path = MazeSolver(maze).solve()
    solution = path_to_directions(path)
    try:
        write_output(config.output_file, maze, config.entry,
                     config.exit, solution)
    except OutputError as e:
        print(f"Error: {e}")
        sys.exit(1)
    # TODO: entry/exit is still hardcoded in mazegen!


if __name__ == "__main__":
    main()
