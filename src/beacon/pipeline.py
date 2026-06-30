"""Compatibility entrypoint for the runtime pipeline."""

from beacon.runtime.pipeline import answer_question, ask_database, main

__all__ = ["answer_question", "ask_database", "main"]


if __name__ == "__main__":
    main()

