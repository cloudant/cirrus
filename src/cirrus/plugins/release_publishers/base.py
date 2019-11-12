from abc import ABCMeta, abstractmethod

from cirrus.configuration import load_configuration


class ReleaseInfoExtractor(metaclass=ABCMeta):
    """
    Abstract base class for subclasses wishing to extract info into
    servicenow.TicketArgs
    """
    _plugin = None

    def __init__(self, config=None):
        self.config = config or load_configuration()

    @abstractmethod
    def get_service_now_params(self, id_, params=None):
        """
        :param str id: identifier used to find external information
        :param dict params: optionally a dictionary may be provided as a
        starting point for creating the ticket paramerters

        :returns: SN Ticket arguments
        :rtype: utilitarian.servicenow.TicketArgs
        """
        pass
