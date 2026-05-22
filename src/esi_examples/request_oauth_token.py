import logging
from urllib.parse import urlencode

from esi_examples.helpers.code_challenge import generate_code_challenge_and_verifier
from esi_examples.helpers.oauth_tokens import request_token
from esi_examples.helpers.secure_random_string import generate_secure_random_string

from .models.auth import AuthenticationRequestParams, EsiAppCredentials

logger = logging.getLogger(__name__)

METADATA_ENDPOINT = "https://login.eveonline.com/.well-known/oauth-authorization-server"
AUTHORIZATION_ENDPOINT = "https://login.eveonline.com/v2/oauth/authorize"
TOKEN_ENDPOINT = "https://login.eveonline.com/v2/oauth/token"


def generate_url(
    code_challenge: str,
    client_id: str,
    callback_url: str,
    authorization_endpoint: str,
    scopes: list[str],
    state: str,
    code_challenge_method: str = "S256",
) -> str:
    """Generate the URL.

    The URL for the user to visit to authorize the application.
    """
    query_params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": callback_url,
        "scope": " ".join(scopes),
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
    }
    query_string = urlencode(query_params)
    return f"{authorization_endpoint}?{query_string}"


def generate_request_params(
    client_id: str, callback_url: str, authorization_endpoint: str, scopes: list[str]
) -> AuthenticationRequestParams:
    """Generate the request parameters for the authentication request."""
    pkce_codes = generate_code_challenge_and_verifier()
    state = generate_secure_random_string(16)
    return AuthenticationRequestParams(
        redirect_url=generate_url(
            code_challenge=pkce_codes.code_challenge,
            client_id=client_id,
            callback_url=callback_url,
            authorization_endpoint=authorization_endpoint,
            scopes=scopes,
            state=state,
        ),
        state=state,
        code_verifier=pkce_codes.code_verifier,
        code_challenge=pkce_codes.code_challenge,
    )


def start_web_server_and_listen_for_code(redirect_url: str, expected_state: str) -> str:
    """Start a simple web server to listen for the callback with the authorization code."""
    # This function needs to be implemented. It should start a web server that listens for the redirect URL,
    # extract the authorization code and state from the query parameters, validate the state, and return the authorization code.
    pass


if __name__ == "__main__":
    import argparse
    import json
    import sys
    from pathlib import Path

    parser = argparse.ArgumentParser(
        description="Get Authorization code for ESI API Oauth Token."
    )
    parser.add_argument(
        "infile",
        nargs="?",
        default=None,
        help="input app credential file or '-' for stdin (default: stdin)",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=None,
        help="The output YAML file to save the authorization code to (default: stdout)",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="The number of spaces to use for indentation in the JSON output (default: %(default)s)",
    )
    args = parser.parse_args()

    # Read JSON input, either from file or stdin ('-' means stdin)
    if args.infile and args.infile != "-":
        input_path = Path(args.infile)
        with input_path.open("r", encoding="utf-8") as f:
            json_input = f.read()
    else:
        json_input = sys.stdin.read()

    # Convert JSON to credential model
    credentials = EsiAppCredentials(**json.loads(json_input))
    auth_request_params = generate_request_params(
        client_id=credentials.clientId,
        callback_url=credentials.callbackUrl,
        authorization_endpoint=AUTHORIZATION_ENDPOINT,
        scopes=credentials.scopes,
    )

    # start a simple HTTP server to listen for the callback with the authorization code - needs function.
    # auto open system webbrowser to the URL
    # Once the authorization code is received, exchange it for an oauth token.
    # output the oauth token as JSON to either the specified output file or stdout.

    # # Write YAML output, either to file or stdout
    # if args.output_file:
    #     output_path = args.output_file
    #     with output_path.open("w", encoding="utf-8") as f:
    #         # yaml dumper already adds a newline at the end, so we don't need to add another one
    #         f.write(yaml_output)

    #     print(f"Converted YAML saved to {output_path.resolve()}")
    # else:
    #     # yaml dumper already adds a newline at the end, so we don't need to add another one
    #     print(yaml_output, end="")
