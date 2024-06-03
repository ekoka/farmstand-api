#!/usr/bin/python
# -*- coding: utf-8 -*-

#import os
import subprocess

from thumbor.optimizers import BaseOptimizer

class Optimizer(BaseOptimizer):

    def should_run(self, image_extension, buffer):
        return 'png' in image_extension

    def optimize(self, buffer, input_file, output_file):
        pngquant_path = self.context.config.PNGQUANT_PATH
        command = '{program} -f -o {output_file} {input_file}'.format(
            program=pngquant_path,
            output_file=output_file,
            input_file=input_file
        )
        #os.system(command)
        subprocess.call(command, shell=True)
