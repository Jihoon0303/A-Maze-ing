from dataclasses import dataclass


CONFIGS_NEEDED = [
    "WIDTH",
    "HEIGHT",
    "ENTRY",
    "EXIT",
    "OUTPUT_FILE",
    "PERFECT",
]

OPTIONAL_CONFIGS = [
    "SEED",
]

ALLOWED_CONFIGS = CONFIGS_NEEDED + OPTIONAL_CONFIGS


@dataclass
class Config:
    """ Parsed and validated maze config """

    width: int
    height: int
    entry: tuple[int, int]
    exit: tuple[int, int]
    output_file: str
    perfect: bool
    seed: int | None = None


class ConfigError(Exception):
    """ Raised when the config file is missing / invalid """
    ...


def parse_raw_config(path: str) -> dict[str, str]:
    """
    Opens the config file to:
    - Skip blank lines / comments
    - Reject invalid lines, unknown and duplicate keys (ConfigError)
    Returns config_dict containig all needed config data
    """
    config_dict: dict[str, str] = {}
    try:
        with open(path) as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k_raw, v_raw = line.split("=", maxsplit=1)
                    k = k_raw.strip()
                    v = v_raw.strip()
                    if k not in ALLOWED_CONFIGS:
                        raise ConfigError(f"Unknown config key: '{k}'")
                    if k in config_dict:
                        raise ConfigError(f"Duplicate config key: '{k}'")
                    if not v:
                        raise ConfigError(f"Empty value for config key: '{k}'")
                    config_dict[k] = v
                else:
                    raise ConfigError(
                        f"Can't read config data from line:\n {line}"
                        )
    except FileNotFoundError:
        raise ConfigError("Config file not found") from None
    except OSError as e:
        raise ConfigError(f"Cannot read config file '{path}': {e}")
    except ValueError as er:
        raise ConfigError(f"Invalid config file: {er}")

    return config_dict


# helpers:
# _____________________________________________________________________________
def parse_coords(raw: str, width: int, height: int,
                 field: str) -> tuple[int, int]:
    """Parses x,y string into actual coordinate tuple and checks bounds"""
    try:
        parts = raw.split(",")
        if len(parts) == 2:
            x = int(parts[0])
            y = int(parts[1])
        else:
            raise ConfigError(f"{field} is not 2 dimensional (x,y)")
        if 0 <= y < height and 0 <= x < width:
            return (x, y)
        else:
            raise ConfigError(f"{field} is out of bounds: {x},{y}")
    except ValueError:
        raise ConfigError(f"Cant create {field}: Value differs from int")


def validate_bounds(boundry: int) -> bool:
    """ Checks for non-positive boundry """
    if boundry <= 0:
        return False
    else:
        return True
# _____________________________________________________________________________


def validate_config(config_dict: dict[str, str]) -> Config:
    """
    Build a validated Config from raw string key/value pairs.

    Converts WIDTH, HEIGHT, ENTRY, EXIT, PERFECT and SEED into their
    proper types, checks that mandatory keys are present and that
    bounds/entry/exit are valid, and raises ConfigError otherwise.
    """
    missing_configs = [k for k in CONFIGS_NEEDED if k not in config_dict]
    if missing_configs:
        raise ConfigError(f"Missing Configs:\n {', '.join(missing_configs)}")
    try:
        width = int(config_dict["WIDTH"])
        height = int(config_dict["HEIGHT"])
    except ValueError:
        raise ConfigError("Can't convert width, height to int")
    if not all([validate_bounds(width), validate_bounds(height)]):
        raise ConfigError(f"Invalid bounds: {width},{height}")
    entry = parse_coords(config_dict["ENTRY"], width, height, "ENTRY")
    exit_point = parse_coords(config_dict["EXIT"], width, height, "EXIT")
    if entry == exit_point:
        raise ConfigError("ENTRY and EXIT must be different")
    perfect_raw = config_dict["PERFECT"].lower()
    if perfect_raw not in ("true", "false"):
        raise ConfigError(
            f"Invalid PERFECT value: '{config_dict['PERFECT']}' "
            "must be True or False"
            )
    perfect_mode = perfect_raw == "true"
    if "SEED" in config_dict:
        try:
            seed = int(config_dict["SEED"])
        except ValueError:
            raise ConfigError(
                f"Invalid seed type: {type(config_dict['SEED'])} "
                "must be int or None"
                )
    else:
        seed = None
    return Config(
        width=width,
        height=height,
        entry=entry,
        exit=exit_point,
        output_file=config_dict["OUTPUT_FILE"],
        perfect=perfect_mode,
        seed=seed
    )


def parse_config(path: str) -> Config:
    """Read and validate a maze configuration file."""
    raw = parse_raw_config(path)
    return validate_config(raw)
