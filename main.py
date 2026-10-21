"""Register FoundryMathAgent or run a stateless terminal conversation."""

import argparse
import logging
import os
import sys
from contextlib import ExitStack
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.core.exceptions import AzureError
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from openai import OpenAIError

from foundry_agent import AGENT_NAME, FoundryMathAgent, build_definition, validate_definition
from math_tools import reject_request


def main() -> int:
    parser = argparse.ArgumentParser(description="FoundryMathAgent: tool-only arithmetic")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--deploy", action="store_true", help="Create a remote prompt-agent version")
    mode.add_argument("--prompt", help="Solve one query and exit")
    parser.add_argument("--verbose", action="store_true", help="Show tool names on stderr")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    logging.getLogger("foundry_agent").setLevel(logging.INFO if args.verbose else logging.WARNING)
    load_dotenv(Path(__file__).with_name(".env"))
    endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT", "").strip()
    model = os.getenv("FOUNDRY_MODEL_NAME", "gpt-5.4-nano").strip()
    version = os.getenv("FOUNDRY_AGENT_VERSION", "").strip()
    if not endpoint or not model or (not args.deploy and not version):
        print("Set FOUNDRY_PROJECT_ENDPOINT, FOUNDRY_MODEL_NAME and (after --deploy) FOUNDRY_AGENT_VERSION in .env.", file=sys.stderr)
        return 2
    try:
        with ExitStack() as stack:
            credential = stack.enter_context(DefaultAzureCredential())
            project = stack.enter_context(AIProjectClient(endpoint=endpoint, credential=credential))
            if args.deploy:
                agent = project.agents.create_version(
                    agent_name=AGENT_NAME,
                    definition=build_definition(model),
                    description="Tool-only arithmetic; web search is not enabled.",
                )
                print(f"Registered {agent.name} version {agent.version}")
                print(f"Set FOUNDRY_AGENT_VERSION={agent.version} in .env")
                return 0
            remote = project.agents.get_version(agent_name=AGENT_NAME, agent_version=version)
            validate_definition(remote.definition, model)
            client = stack.enter_context(project.get_openai_client())
            client = client.with_options(timeout=30.0, max_retries=2)
            agent = FoundryMathAgent(client, version)
            if args.prompt is not None:
                print(agent.solve(args.prompt))
                return 0
            print(f"{AGENT_NAME} (type exit to quit)")
            while True:
                try:
                    prompt = input("You: ")
                except EOFError:
                    break
                if prompt.strip().lower() in {"exit", "quit"}:
                    break
                print(f"Agent: {agent.solve(prompt)}")
    except (AzureError, OpenAIError, ValueError) as error:
        print(reject_request())
        print(f"Foundry error ({type(error).__name__}); check endpoint, login, RBAC, model and agent version.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())