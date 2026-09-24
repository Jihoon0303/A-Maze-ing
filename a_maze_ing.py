import sys

from config import Config, ConfigError, parse_config
from display import WALL_COLORS, get_42_logo, print_grid, render_grid
from mazegen.maze import Cell, Maze
from mazegen.maze_generator import MazeGenerator
from mazegen.maze_solver import MazeSolver
from output import OutputError, path_to_directions, write_output


# Wall colors can't be the same as path or logo
WALL_CYCLE_COLORS = [
    color for color in WALL_COLORS
    if color not in ("magenta", "cyan")
]


def generate_and_write(config: Config) -> tuple[Maze, list[Cell]]:
    """Generate a maze, solve it, and write the output file."""
    maze = Maze(config.width, config.height)
    MazeGenerator(maze, config.entry, config.exit, config.perfect).generate()
    path = MazeSolver(maze, config.entry, config.exit).solve()
    solution = path_to_directions(path)
    write_output(
        config.output_file, maze, config.entry, config.exit, solution
    )
    return maze, path


def main() -> None:
    """Parse config, then run the interactive maze display loop."""
    if len(sys.argv) != 2:
        print(f"Usage: python3 {sys.argv[0]} <config_file>")
        return
    try:
        config = parse_config(sys.argv[1])
    except ConfigError as e:
        print(f"Error: {e}")
        return

    try:
        maze, path = generate_and_write(config)
    except OutputError as e:
        print(f"Error: {e}")
        return

    colors = WALL_CYCLE_COLORS
    color_index = 0
    show_path = True

    while True:
        grid = render_grid(
            maze, config.entry, config.exit, path if show_path else []
        )
        print_grid(grid, colors[color_index], get_42_logo(maze))

        print("=== A-Maze-ing ===")
        print("1. Re-generate a new maze")
        print("2. Show/Hide path from entry to exit")
        print("3. Change maze wall colours")
        print("4. Quit")
        try:
            choice = input("Choice? (1-4): ").strip()
        except EOFError:
            break

        if choice == "1":
            try:
                maze, path = generate_and_write(config)
            except OutputError as e:
                print(f"Error: {e}")
                return
        elif choice == "2":
            show_path = not show_path
        elif choice == "3":
            color_index = (color_index + 1) % len(colors)
        elif choice == "4":
            break
        else:
            print("\nInvalid choice!")
            try:
                input("\nPress Enter and try again with (1-4)")
            except EOFError:
                break


if __name__ == "__main__":
    main()
