#!/usr/bin/python
# -*- coding: utf-8 -*-

# CUSTOM FILTER FOR CCA PROJECT
# BRAZEN SOLUTIONS

from thumbor.filters import BaseFilter, filter_method
from thumbor.utils import logger
from PIL.ImageOps import colorize

class Filter(BaseFilter):

    @filter_method(BaseFilter.String)
    def monochrome_tint(self, color):
        
        if self.engine.image.mode == "I":
            table=[ i/256 for i in range(65536) ]
            self.engine.image = self.engine.image.point(table,'L')
        else:
            self.engine.image = self.engine.image.convert('L')
        self.engine.image = colorize(self.engine.image, '#'+color, '#ffffff')