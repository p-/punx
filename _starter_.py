#!/usr/bin/env python

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

# if len(sys.argv) == 1:
#     # developer use
#     sys.argv.append("validate")
#     sys.argv.append("src/punx/data/compression.h5")
#     sys.argv.append("src/punx/data/writer_1_3.hdf5")


from punx import main
print(main.__file__)
main.main()