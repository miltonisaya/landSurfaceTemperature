# -*- coding: utf-8 -*-
"""Land Surface Temperature Processing provider."""

from qgis.core import QgsProcessingProvider

from .landsat_ndvi import LandsatNdviAlgorithm
from .aster_ndvi import AsterNdviAlgorithm
from .tm_radiance import TmRadianceAlgorithm
from .etm_radiance import EtmRadianceAlgorithm
from .tirs_radiance import TirsRadianceAlgorithm
from .aster_radiance import AsterRadianceAlgorithm
from .brightness_temperature import BrightnessTemperatureAlgorithm
from .zhang_lse import ZhangLseAlgorithm
from .ndvi_threshold_lse import NdviThresholdLseAlgorithm
from .aster_lse import AsterLseAlgorithm
from .planck_lst import PlanckLstAlgorithm
from .mono_window import MonoWindowAlgorithm
from .single_channel import SingleChannelAlgorithm
from .radiative_transfer import RadiativeTransferAlgorithm
from .aster_single_channel import AsterSingleChannelAlgorithm
from .aster_split_window import AsterSplitWindowAlgorithm


class LstProvider(QgsProcessingProvider):

    def id(self):
        return 'lst'

    def name(self):
        return 'Land Surface Temperature'

    def longName(self):
        return 'Land Surface Temperature Estimation'

    def loadAlgorithms(self):
        self.addAlgorithm(LandsatNdviAlgorithm())
        self.addAlgorithm(AsterNdviAlgorithm())
        self.addAlgorithm(TmRadianceAlgorithm())
        self.addAlgorithm(EtmRadianceAlgorithm())
        self.addAlgorithm(TirsRadianceAlgorithm())
        self.addAlgorithm(AsterRadianceAlgorithm())
        self.addAlgorithm(BrightnessTemperatureAlgorithm())
        self.addAlgorithm(ZhangLseAlgorithm())
        self.addAlgorithm(NdviThresholdLseAlgorithm())
        self.addAlgorithm(AsterLseAlgorithm())
        self.addAlgorithm(PlanckLstAlgorithm())
        self.addAlgorithm(MonoWindowAlgorithm())
        self.addAlgorithm(SingleChannelAlgorithm())
        self.addAlgorithm(RadiativeTransferAlgorithm())
        self.addAlgorithm(AsterSingleChannelAlgorithm())
        self.addAlgorithm(AsterSplitWindowAlgorithm())
