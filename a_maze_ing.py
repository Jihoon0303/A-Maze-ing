import sys
from config import ConfigError, parse_config
from output import OutputError, write_output
from mazegen.maze_generator import MazeGenerator


def main() -> None:
    """ Creates config instance and catches Usage errors"""
    if len(sys.argv) != 2:
        print(f"Usage: python3 {sys.argv[0]} <config_file>")
        sys.exit(1)
    try:
        config = parse_config(sys.argv[1])
    except ConfigError as e:
        print(f"Error: {e}")
        sys.exit(1)
    # placeholders:
    try:
        maze = Maze()
        write_output("output_maze.txt")
    
    # replace later with:
    # Build a Maze from config.width/config.height
    # generate it with the seed, entry/exit and perfect flag
    # solve the maze with shortest path
    # Write output file
    # run display loop


if __name__ == "__main__":
    main()
