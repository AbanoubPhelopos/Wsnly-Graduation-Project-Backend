from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Any
from src.Core.Application.Common.Models.Result import Result

TResponse = TypeVar("TResponse")
TCommand = TypeVar("TCommand")
TQuery = TypeVar("TQuery")


class ICommand(ABC):
    """Marker interface for Commands."""

    pass


class IQuery(Generic[TResponse], ABC):
    """Marker interface for Queries."""

    pass


class ICommandHandler(Generic[TCommand, TResponse], ABC):
    @abstractmethod
    def handle(self, command: TCommand) -> Result[TResponse]:
        pass


class IQueryHandler(Generic[TQuery, TResponse], ABC):
    @abstractmethod
    def handle(self, query: TQuery) -> Result[TResponse]:
        pass
