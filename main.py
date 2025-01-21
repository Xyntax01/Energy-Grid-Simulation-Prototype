#!/usr/bin/env python

import argparse
import asyncio
import logging
import os
import sys
from typing import List

from dotenv import load_dotenv

from src.factories.real_agent_factory import RealAgentFactory
from src.simulation_runner import SimulationRunner
from src.utils.logger import valid_log_threshold


def parse_cmd_opts(argv: List[str]) -> argparse.Namespace:
    """Argument parsing. defines what arguments there are, their defaults and other ways of setting them, and provides documentation on how to use the program.

    Args:
        argv: The command line arguments in string format that are to be parsed."""
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--domain",
        "-d",
        type=str,
        default=os.getenv("DOMAIN", "localhost"),
        help='Set the domain used in messaging. Also possible to set via the envvar `DOMAIN`. Defaults to "localhost"',
    )
    parser.add_argument(
        "--configuration_file",
        "-c",
        type=str,
        default=os.getenv("CONFIG", "config.yaml"),
        help='The path to the config yaml file which describes the network which is to be simulated. Also possible to set via the envvar `CONFIG`. Defaults to "config.yaml"',
    )
    parser.add_argument(
        "--password",
        "-p",
        type=str,
        default="password",
        help='The password to be used in messaging. Defaults to "password"',
    )
    parser.add_argument(
        "--logfile",
        "-l",
        type=str,
        default=os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "logs", "sim_run.log"
        ),
        help='Logfile to write logs to, defaults to "sim_run.log"',
    )
    parser.add_argument(
        "--log_threshold",
        "-t",
        type=str,
        choices=list(logging._nameToLevel.keys()),
        default="INFO",
        help="A logging threshold. Agents log everything to console and logfiles that is higher than this threshold. The default value for this threshold is INFO, meaning everything gets logged. This threshold is the default for all agents and get overridden by the threshold set in the config per agent.",
    )

    args = parser.parse_args(argv[:])

    threshold_level = valid_log_threshold(args.log_threshold)
    args.log_threshold = threshold_level if threshold_level else "INFO"

    return args


def main(argv: List[str]) -> None:
    """Main entrypoint of the application. it defines where to parse input and what the entrypoint runs.

    Args:
        argv: the command line arguments in string format which are to be parsed."""
    args = parse_cmd_opts(argv[:])

    runner = SimulationRunner(args, agent_factory=RealAgentFactory())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(runner.run())


if __name__ == "__main__":
    main(sys.argv[1:])
