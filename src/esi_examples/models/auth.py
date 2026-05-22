from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class EsiAppCredentials:
    """EVE application credentials.

    Field names match the JSON keys returned by the ESI app registration page.
    https://developers.eveonline.com/applications
    """

    name: str
    description: str
    clientId: str
    clientSecret: str
    callbackUrl: str
    scopes: list[str] = field(default_factory=list[str])