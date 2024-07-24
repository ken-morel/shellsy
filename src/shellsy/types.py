from decimal import Decimal


class Int(int):
    @classmethod
    def from_string(cls, str):
        return cls(str)


class Float(Decimal):
    @classmethod
    def from_string(cls, str):
        return cls(str)


class Str(str):
    @classmethod
    def from_string(cls, str):
        return cls(str)
