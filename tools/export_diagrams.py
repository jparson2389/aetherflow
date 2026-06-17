import argparse
import subprocess
from pathlib import Path

from loguru import logger


def derive_output_path(input_path: str, output_format: str) -> Path:
    """Derive an output path from an input markdown path.

    Args:
        input_path: Path to the markdown file containing Mermaid diagrams.
        output_format: Output extension (for example, png or svg).

    Returns:
        A path under assets/ with the same relative structure when input is
        under docs/, otherwise assets/diagrams/<name>.<format>.

    """
    input_file = Path(input_path).expanduser()
    output_name = f'{input_file.stem}.{output_format}'
    cwd = Path.cwd()

    normalized_parts = input_file.parts
    if input_file.is_absolute():
        try:
            normalized_parts = input_file.relative_to(cwd).parts
        except ValueError:
            normalized_parts = input_file.parts

    docs_index = next((i for i, part in enumerate(normalized_parts) if part == 'docs'), -1)
    if docs_index != -1:
        relative_parts = normalized_parts[docs_index + 1 : -1]
        return Path('assets', *relative_parts, output_name)

    return Path('assets', 'diagrams', output_name)


def export_mermaid_diagrams(
    input_path: str,
    output_path: str,
    scale: int,
    width: int,
    height: int | None,
) -> int:
    """Export Mermaid diagrams from a markdown file using mmdc.

    Args:
        input_path: The relative path to the input .md file.
        output_path: The relative path to the output file.
        scale: Mermaid rendering scale factor.
        width: Mermaid rendering width in pixels.
        height: Mermaid rendering height in pixels or None.

    Returns:
        Zero when export succeeds, non-zero when export fails.

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
        '-s',
        str(scale),
        '-w',
        str(width),
    ]
    if height is not None:
        command.extend(['-H', str(height)])

    try:
        logger.info(f'Exporting diagrams from {input_file} to {output_file}...')
        subprocess.run(command, check=True, capture_output=True, text=True)

        if not output_file.exists():
            numbered_outputs = sorted(
                output_file.parent.glob(f'{output_file.stem}-*{output_file.suffix}')
            )
            if len(numbered_outputs) == 1:
                numbered_outputs[0].replace(output_file)
                logger.info(
                    'Mermaid CLI emitted a numbered output; normalized to '
                    f'{output_file}.'
                )
            elif len(numbered_outputs) > 1:
                logger.error(
                    'Mermaid CLI emitted multiple numbered outputs and no '
                    f'direct output path: {numbered_outputs}'
                )
                return 1

        if not output_file.exists():
            logger.error(
                'Mermaid CLI exited successfully but no output artifact was '
                f'created at {output_file}.'
            )
            return 1

        logger.success('Export completed successfully.')
        return 0
    except subprocess.CalledProcessError as e:
        logger.error(f'Failed to export diagrams: {e.stderr}')
        return 1
    except FileNotFoundError:
        logger.error('Mermaid CLI (mmdc) not found. Ensure it is installed via npm.')
        return 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Export Mermaid diagrams from a markdown file.'
    )
    parser.add_argument(
        'input_path',
        nargs='?',
        default='docs/architecture/system-overview.md',
        help='Path to the markdown file containing Mermaid diagram(s).',
    )
    parser.add_argument(
        'output_path',
        nargs='?',
        default=None,
        help='Optional output path. If omitted, one is derived under assets/.',
    )
    parser.add_argument(
        '--format',
        choices=['png', 'svg'],
        default='png',
        help='Output format used when output_path is omitted. Default: png.',
    )
    parser.add_argument(
        '--scale',
        type=int,
        default=3,
        help='Mermaid render scale factor. Default: 3.',
    )
    parser.add_argument(
        '--width',
        type=int,
        default=3200,
        help='Mermaid render width in pixels. Default: 3200.',
    )
    parser.add_argument(
        '--height',
        type=int,
        default=None,
        help='Optional Mermaid render height in pixels.',
    )
    args = parser.parse_args()

    resolved_output_path = args.output_path or str(
        derive_output_path(args.input_path, args.format)
    )

    status = export_mermaid_diagrams(
        input_path=args.input_path,
        output_path=resolved_output_path,
        scale=args.scale,
        width=args.width,
        height=args.height,
    )
    raise SystemExit(status)
