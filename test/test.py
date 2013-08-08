__author__ = 'Lukas'

from atlasengine import AtlasEngine
import logging


if __name__ == "__main__":
   ae = AtlasEngine()

   # configure logging
   logging.basicConfig(level=logging.DEBUG)
   logging.info('Importing magnitudes for basel...')

   # import basel magnitudes from csv into history
   csv_path = 'cat.dat'
   ae.event_history.import_from_csv(csv_path)
   logging.info('done')

   # run engine
   ae.run()