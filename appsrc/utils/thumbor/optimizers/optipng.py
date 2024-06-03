#!/usr/bin/python
# -*- coding: utf-8 -*-

#import os
import subprocess 

from thumbor.optimizers import BaseOptimizer

class Optimizer(BaseOptimizer):

    def should_run(self, image_extension, buffer):
        return 'png' in image_extension

    def optimize(self, buffer, input_file, output_file):
        optipng_path = self.context.config.OPTIPNG_PATH
        command = '{program} -o {compression_level} ' 
        '-out {output_file} {input_file}'
        command.format(
            program=optipng_path,
            compression_level=2, # 2 is the default
            output_file=output_file,
            input_file=input_file,
        )

        #os.system(command)
        subprocess.system(command)


