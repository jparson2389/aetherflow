import subprocess
from pathlib import Path

from loguru import logger


def export_mermaid_diagrams(input_path: str, output_path: str) -> None:
    """Export Mermaid diagrams from a markdown file to a PNG image using mmdc.

    Args:
        input_path (str): The relative path to the input .md file.
        output_path (str): The relative path to the output .png file.

    """
    input_file = Path(input_path)
    output_file = Path(output_path)

    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)

    command = [
        'mmdc',
        '-i',
        str(input_file),
        '-o',
        str(output_file),
        '-b',
        'transparent',
    ]

    try:
        logger.info(f'Exporting diagrams from {input_file} to {output_file}...')
        subprocess.run(command, check=True, capture_output=True, text=True)
        logger.success('Export completed successfully.')
    except subprocess.CalledProcessError as e:
        logger.error(f'Failed to export diagrams: {e.stderr}')
    except FileNotFoundError:
        logger.error('Mermaid CLI (mmdc) not found. Ensure it is installed via npm.')


if __name__ == '__main__':
    export_mermaid_diagrams(
        input_path='docs/architecture/system-overview.md',
        output_path='assets/architecture/system-overview.png',
    )
