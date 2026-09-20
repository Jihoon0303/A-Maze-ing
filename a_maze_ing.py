import sys
from config import ConfigError, parse_config
from output import OutputError, write_output
from mazegen.maze_generator import MazeGenerator
from mazegen.maze import Maze


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
    generator = MazeGenerator(maze)
    generator.generate()
    try:
        write_output(config.output_file, maze, config.entry,
                     config.exit, "")  # "" is placeholder for solved path
    except OutputError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # replace later with:
    # Build a Maze from config.width/config.height
    # generate it with the seed, entry/exit and perfect flag
    # solve the maze with shortest path
    # Write output file
    # run display loop


if __name__ == "__main__":
    main()
