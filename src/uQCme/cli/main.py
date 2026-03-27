#!/usr/bin/env python3
"""
uQCme - Microbial Quality Control CLI Tool

A command-line tool for processing microbial sequencing QC data against
configurable quality control rules and tests.
"""

import argparse
import sys
from typing import Dict, Any, Optional
from uQCme.core.engine import QCProcessor
from uQCme.core.exceptions import UQCMeError


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='uQCme - Microbial Quality Control CLI Tool'
    )
    parser.add_argument(
        '--config',
        required=False,
        help='Path to configuration YAML file'
    )
    
    # Add data override arguments
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--file',
        help='Override data source with a local file path'
    )
    group.add_argument(
        '--api-call',
        help='Override data source with an API URL'
    )
    parser.add_argument(
        '--api-bearer-token',
        help='Bearer token used with --api-call for API authentication'
    )
    parser.add_argument(
        '--api-bearer-token-env',
        help='Environment variable name containing bearer token for --api-call'
    )

    args = parser.parse_args()

    # Print header
    print("🔬 uQCme - Microbial Quality Control CLI Tool")
    print("=" * 50)

    try:
        if args.file and (args.api_bearer_token or args.api_bearer_token_env):
            parser.error(
                "--api-bearer-token and --api-bearer-token-env require "
                "--api-call"
            )

        # Prepare data override if arguments are provided
        data_override = None
        if args.file:
            data_override = {'file': args.file}
        elif args.api_call:
            data_override = {'api_call': args.api_call}
            if args.api_bearer_token:
                data_override['api_bearer_token'] = args.api_bearer_token
            if args.api_bearer_token_env:
                data_override['api_bearer_token_env'] = (
                    args.api_bearer_token_env
                )

        # Initialize processor with optional override
        processor = QCProcessor(args.config, data_override=data_override)

        # Load input data
        processor.load_input_files()

        # Process samples
        processor.process_samples()

        # Save results
        processor.save_results()
        
        # Save warnings
        processor.save_warnings()

        # Print summary
        processor.print_summary()

        print("\n✅ QC processing completed successfully!")

    except KeyboardInterrupt:
        print("\n⚠️ Processing interrupted by user")
        sys.exit(1)
    except UQCMeError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
