import sys
from argparse import ArgumentParser, BooleanOptionalAction
from typing import Optional, Sequence
import logging
from pathlib import Path
import json
from shutil import rmtree

import bombcell as bc
from bombcell import __version__ as bombcell_version


def set_up_logging():
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logging.info(f"Bombcell version {bombcell_version}")


def find(
    glob: str,
    filter: str = "",
    parent: Path = None,
) -> list:
    """Search for a list of matches to the given glob pattern, optionally filtering results that contain the given filter."""
    if glob.startswith("/"):
        # Search from an absolute path.
        matches = Path("/").glob(glob[1:])
    else:
        # Search from the given or current working directory.
        if parent is None:
            parent = Path()
        matches = parent.glob(glob)
    matching_paths = [match for match in matches if filter in match.as_posix()]
    logging.info(f"Found {len(matching_paths)} matches with filter '{filter}' for pattern: {glob}")
    return matching_paths


def find_one(
    glob: str,
    filter: str = "",
    default: Path = None,
    none_ok: bool = False,
    parent: Path = None,
) -> Path:
    """Search for a single match to the given glob pattern, optionally filtering duplicate glob matches using the given filter."""
    matching_paths = find(glob, filter, parent)
    if len(matching_paths) == 1:
        first_match = matching_paths[0]
        logging.info(f"Found one match: {first_match}")
        return first_match
    elif len(matching_paths) > 1:
        logging.error(f"Found multiple matches, please remove all but one: {matching_paths}")
        raise ValueError(f"Too many matches found.")
    elif default is not None or none_ok:
        return default
    else:
        raise ValueError(f"No match found.")


def load_phy_params(
    params_py: Path
):
    """Phy params.py is a Python script with parameter assignments.  Evaluate it to get a dictionary of parameters."""
    logging.info(f"Loading params.py: {params_py}")
    params = locals()
    exec(params_py.read_text(), globals(), params)
    for k, v in params.items():
        logging.info(f"  {k}: {v}")
    return params


def find_probes_and_run_bombcell(
    phy_path: Path,
    probe_ids: list[str],
    probe_params_pattern: str,
    bombcell_params_pattern: str,
    kilosort_version: int,
    remove_existing_outputs: bool
):
    """Locate run/probe subdirs wiht Kilsort/Phy results, run Bombcel on each in sequence."""

    # If we never find a sorting to analyze, raise an error at the end.
    sorting_count = 0

    # Locate runs as subfolders of the phy_path.
    logging.info(f"Processing Kilsort/Phy runs within: {phy_path}")
    phy_run_paths = [run_dir for run_dir in phy_path.iterdir() if run_dir.is_dir()]
    logging.info(f"Found {len(phy_run_paths)} Kilosort/Phy run dirs: {phy_run_paths}")
    if not phy_run_paths:
        raise ValueError("Found no Kilosort/Phy run dirs to process.")

    for probe_id in probe_ids:
        logging.info(f"Looking for probe {probe_id}")

        # Find probe-specific or default Bombcell params.
        bombcell_user_params_path = find_one(bombcell_params_pattern, filter=probe_id, none_ok=True)
        if bombcell_user_params_path is None:
            logging.warning(f"Using only default Bombcell parameters for probe {probe_id}.")
            bombcell_user_params = {}
        else:
            logging.info(f"Loading Bombcell parameters from JSON for probe {probe_id}: {bombcell_user_params_path}")
            with open(bombcell_user_params_path, 'r') as parameters_in:
                bombcell_user_params = json.load(parameters_in)

        for phy_run_path in phy_run_paths:
            logging.info(f"Processing Kilosort/Phy run dir: {phy_run_path}")

            params_path = find_one(probe_params_pattern, filter=probe_id, parent=phy_run_path, none_ok=True)
            if params_path is None:
                logging.warning(f"Found no params.py for probe {probe_id} within {phy_run_path}")
                continue

            # We found a sorting to analyze.
            sorting_count += 1

            # Configure Bombcell parameters:
            # - Start with baked-in defaults and let Bombcell read the SpikeGlx .meta info.
            # - Add user-supplied values and overrides, if any.
            phy_params = load_phy_params(params_path)
            phy_dat_path = phy_params['dat_path']
            raw_bin_path = Path(phy_dat_path[0])
            bin_file = raw_bin_path.as_posix()
            meta_file = raw_bin_path.with_suffix(".meta").as_posix()
            phy_path = params_path.parent
            bombcell_params = bc.get_default_parameters(
                phy_path.as_posix(),
                kilosort_version=kilosort_version,
                raw_file=bin_file,
                meta_file=meta_file,
            )
            bombcell_params['ephys_sample_rate'] = phy_params['sample_rate']
            bombcell_params['nChannels'] = phy_params['n_channels_dat']

            probe_bombcell_output_path = Path(phy_path, "bombcell")
            if remove_existing_outputs and probe_bombcell_output_path.exists():
                logging.warning(f"Removing existing Bombcell outputs for probe {probe_id}: {probe_bombcell_output_path}")
                rmtree(probe_bombcell_output_path)
            probe_bombcell_output_path.mkdir(exist_ok=True, parents=True)
            bombcell_params['savePlots'] = True
            bombcell_params['plotsSaveDir'] = probe_bombcell_output_path.as_posix()

            if bombcell_user_params:
                logging.info(f"Setting {len(bombcell_user_params)} user-supplied Bombcell params:")
                for name, value in bombcell_user_params.items():
                    logging.info(f"  {name} = {value}")
                    bombcell_params[name] = value

            bombcel_effective_params_path = Path(phy_path, f"{probe_id}-bombcell-effective-parameters.json")
            logging.info(f"Saving effective Bombcell paremeters: {bombcel_effective_params_path}")
            with open(bombcel_effective_params_path, 'w') as parameters_out:
                json.dump(bombcell_params, parameters_out)

            logging.info("Running Bombcell:")
            bc.run_bombcell(
                phy_path,
                probe_bombcell_output_path,
                bombcell_params,
                return_figures=False,
                save_figures=True
            )
            logging.info("OK\n")

    logging.info(f"Completed Bombcell for {sorting_count} sortings.")
    if sorting_count < 1:
        raise ValueError(f"Found no sortings for bombcell matching probe ids: {probe_ids}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    set_up_logging()

    parser = ArgumentParser(description="Analyze one or more sortings from Kilosort/Phy.")

    parser.add_argument(
        "phy_root",
        type=str,
        help="directory with Phy/Kilosort outputs from one or more runs"
    )
    parser.add_argument(
        "--probe-ids",
        type=str,
        nargs="+",
        help="One or more probe ids to consider for sorting and for associating probes with Bombcell parameters. (default: %(default)s)",
        default=["imec0", "imec1"]
    )
    parser.add_argument(
        "--probe-params-pattern",
        type=str,
        help="glob to match one params.py file per probe, within PHY_ROOT, for each run. (default: %(default)s)",
        default="*/params.py"
    )
    parser.add_argument(
        "--bombcell-params-pattern",
        type=str,
        help="Glob pattern used to search for JSON files with bombcell parameters. (default: %(default)s)",
        default="**/*-bombcell-parameters.json"
    )
    parser.add_argument(
        "--kilosort-version",
        type=int,
        help="Which version of Kilosort was used? (default: %(default)s)",
        default=4
    )
    parser.add_argument(
        "--remove-existing-outputs",
        action=BooleanOptionalAction,
        help="Whether or not to remove existing (stale) Bombcell outputs for each probe, before running Bombcell. (default: %(default)s)",
        default=True
    )

    cli_args = parser.parse_args(argv)

    phy_path = Path(cli_args.phy_root)
    try:
        find_probes_and_run_bombcell(
            phy_path,
            cli_args.probe_ids,
            cli_args.probe_params_pattern,
            cli_args.bombcell_params_pattern,
            cli_args.kilosort_version,
            cli_args.remove_existing_outputs
        )
    except:
        logging.error("Error running bombcell.", exc_info=True)
        return -1


if __name__ == "__main__":
    exit_code = main(sys.argv[1:])
    sys.exit(exit_code)
