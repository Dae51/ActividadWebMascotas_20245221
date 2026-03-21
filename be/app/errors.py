class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        detail: str,
        code: str = "bad_request",
        errors: list[dict] | None = None,
    ) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.code = code
        self.errors = errors
