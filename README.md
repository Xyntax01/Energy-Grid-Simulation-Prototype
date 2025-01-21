# Energy Grid Simulation Prototype

![nox workflow](https://github.com/Xyntax01/Energy-Grid-Simulation-Prototype/blob/main/.github/workflows/ci.yml/badge.svg)

This prototype simulates the Dutch energy grid, it includes agents such as:

- Solar panels
- Wind turbines
- Charging stations
- Time
- Weather

The agents are able to communicate with each other and make decisions based on the information they receive. The simulation is built using the [Spade](https://spade-mas.readthedocs.io/en/latest/index.html) framework, which facilitates the creation and management of multi-agent systems.

Key components of the simulation include:

- **Agents**: Represent different entities in the energy grid such as solar panels, wind turbines, and charging stations. Each agent can perform specific behaviors and interact with other agents.
- **Behaviors**: Define the actions that agents can perform. Examples include `CyclicBehaviour` for repetitive tasks and `OneShotBehaviour` for single actions.
- **Logger**: Utilizes the [`LoggerFactory`](src/utils/logger.py) to manage logging across the simulation.
- **Configuration**: The simulation can be configured using a YAML file, which defines the network and its assets.

The project structure is organized as follows:

- `src/agents`: Contains the agent implementations.
- `src/utils`: Utility functions and classes.
- `tests`: Unit tests for the simulation.

## Prerequisites

To run the simulation, ensure you have [Docker](https://www.docker.com/get-started/) installed.

## Running the Simulation

Execute the following command to build the Docker image, start the container, and log the output:

```bash
docker compose up -d --build && docker logs simulation -n 0 -f
```

Docker will build the python image with the latest code, start the container and log the output to your console.

## Spade

Spade is a Multi-Agent Based (MAS) simulation framework that is used by the simulation. The official documentation can be found at [spade-mas.readthedocs.io](https://spade-mas.readthedocs.io/en/latest/index.html).

## Nox usage

[`nox`](https://nox.thea.codes/en/stable/index.html) is a command-line tool that automates testing in multiple Python environments, similar to [tox](https://tox.readthedocs.org/).

To run the tests, run the following command:

```bash
nox
```

To see the code coverage in more detail, open the `htmlcov\index.html` file.

## Configuring a network

A network with assets can be configured using a yaml configuration file. This file configures a root network and defines all the other assets and (sub)networks as it's children. Documentation and an example configuration file can be found [here](./docs/configuration.md).

## Configuration
This simulation requires Python 3.9 or higher. Make sure to install dependencies using:
```bash
pip install -r requirements.txt
```

Logging can be configured via [`LoggerFactory`](src/utils/logger.py). You can adjust log levels by editing the configuration in the `LoggerFactory` class or by setting environment variables in your Docker setup.

To modify Docker environment variables for the container, you can add them to the `docker-compose.yml` file under the `environment` section.

## Instantiating nodes

## Adding a new agent

- Create a new class that implements `spade.agent.Agent`.
- Create a new behaviour class that implements e.g., `CyclicBehaviour` and create an instance called `self.behaviour` in
  the agent class.
- In the agent class, create an async function called `setup`.
- In this function, call `self.add_behaviour(self.behaviour)` with the behaviour class to implement this behaviour.
