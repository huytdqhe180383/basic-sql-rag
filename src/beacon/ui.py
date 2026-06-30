"""Compatibility entrypoint for the Gradio UI."""

from beacon.app.ui import handle_question, main

__all__ = ["handle_question", "main"]


if __name__ == "__main__":
    main()
