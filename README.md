# Energy Grid Simulation Prototype

[![CI](https://github.com/Xyntax01/Congestion-Smart-Charging-Simulation/actions/workflows/ci.yml/badge.svg)](https://github.com/Xyntax01/Congestion-Smart-Charging-Simulation/actions/workflows/ci.yml)

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

1. Create a new class that inherits from either a prosumption or interaction base agent (e.g., BaseProsumptionAgent, BaseInteractionAgent). Implement required methods such as setup(), where you define and add any needed behaviours.
2. Implement at least one behaviour class (e.g., CyclicBehaviour) and add it to your agent in the setup() method.
3. If the agent needs data from weather or time agents, subscribe to them by creating appropriate SubscriptionBehaviours and adding them in setup().
4. In src/factories/agent_factory.py and src/factories/real_agent_factory.py, add references to your class so that your new agent type can be instantiated properly. Update the dictionaries or methods that create and return agent instances to include your new agent.
5. (Optional) If the agent must be part of the simulation network, add configuration details in config.yaml or the relevant network structure, ensuring the asset name and type match your newly added agent.

## Adding Agent Parameters

When creating a new agent, you can add optional parameters by defining them in your agent’s constructor and using them in your behaviours. For example:

- Provide a “factor” argument to scale power usage or generation.
- Allow a “smart” boolean to enable or disable advanced logic.

## Subscribing to Time or Weather

To use time or weather data in your agent:

1. Import SubscriptionBehaviour from src/agents/common_behaviours/subscribeable_behaviour.py.
2. Add a SubscriptionBehaviour to your agent’s setup() method, targeting the TimeAgent or WeatherAgent JID.
3. Implement a callback function (e.g., \_process_weather_message) to handle the incoming data.
4. Update your agent’s internal state and calculations (e.g., net_power_usage_kw, temperature adjustments) based on the subscribed info.
