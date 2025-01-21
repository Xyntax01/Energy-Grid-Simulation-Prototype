def get_time_agent_jid(domain: str) -> str:
    """
    Get the TimeAgent JID.

    Args:
        domain (str): the domain of the XMPP server to use.

    Returns:
        str: the JID of the TimeAgent agent.
    """
    return f"time_agent@{domain}"


def get_weather_agent_jid(domain: str) -> str:
    """
    Get the WeatherAgent JID.

    Args:
        domain (str): the domain of the XMPP server to use.

    Returns:
        str: the JID of the WeatherAgent agent.
    """
    return f"weather_agent@{domain}"


def get_main_network_agent_jid(domain: str) -> str:
    """
    Get the NetworkAgent JID.

    Args:
        domain (str): the domain of the XMPP server to use.

    Returns:
        str: the JID of the NetworkAgent agent.
    """
    return f"main_network@{domain}"


def get_cpo_agent_jid(domain: str) -> str:
    """
    Get the NetworkAgent JID.

    Args:
        domain (str): the domain of the XMPP server to use.

    Returns:
        str: the JID of the NetworkAgent agent.
    """
    return f"cpo_1@{domain}"
