import multiprocessing
import sys


def main() -> None:
    # Bắt buộc cho binary PyInstaller trên Windows (Plan §4.1):
    # tránh tiến trình con chạy lại backend.
    multiprocessing.freeze_support()
    from writestory_be.bootstrap.runtime import main as run

    raise SystemExit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
