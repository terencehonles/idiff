# vi: encoding=utf-8
# -*- coding: utf-8 -*-

from PySide import QtGui as gui
import logging

from views import Window


class Application(gui.QApplication):
    NAME = 'idiff'

    @classmethod
    def _get_parser(cls):
        'creates an option parser and adds the command line arguments'

        try:
            from argparse import ArgumentParser
            parser = ArgumentParser(prog=cls.NAME)
        except ImportError:
            # we're fine with OptionParser because we're using it like
            # ArgumentParser
            from optparse import OptionParser
            parser = OptionParser(prog=cls.NAME,
                                  usage='%prog [options] filenames...')

            parser.add_argument = parser.add_option


        parser.set_defaults(mode=Window.DEFAULT_VIEW,
                            flicker=Window.DEFAULT_FLICKER)

        parser.add_argument('-v', '--view',
                            help='one of {%s}' % ', '.join(Window.VIEWS.keys()))

        parser.add_argument('-t', '--time', dest='flicker',
                            help='time string representing the frequency in '
                                 'which to alternate the images '
                                 '(understands: 1s, 500ms, 2.5s)')

        parser.add_argument('--timer', action='store_const', dest='flicker',
                            const=Window.DEFAULT_FLICKER,
                            help='implies --time %r' % Window.DEFAULT_FLICKER)

        return parser

    @staticmethod
    def _parse_arguments(parser, arguments):
        '''
        parses the arguments with the parser and returns the options and
        filenames
        '''

        try:
            # argument parser
            if hasattr(parser, 'parse_known_args'):
                if parser.get_default('filenames') is None:
                    parser.add_argument('filenames', nargs='*')
                    parser.set_defaults(filenames=[])

                options = parser.parse_args(arguments)
                return options, options.filenames
            else:
                return parser.parse_args(arguments)
        except SystemExit as e:
            # allow a "success" to exit cleanly (otherwise use the GUI)
            if e.code == 0: raise
            if hasattr(parser, 'parse_known_args'):
                return parser.parse_args([]), []
            else:
                return parser.parse_args([])


    def _prompt_for_files(self, count):
        'prompts the user for additional files'

        filenames = []

        while len(filenames) < count:
            # allow the user to select one more file
            if len(filenames) - count == 1:
                selected, filter = gui.QFileDialog.getOpenFileName()
                selected = [selected]

            # allow the user to select one or more files
            else:
                selected, filter = gui.QFileDialog.getOpenFileNames()

            # ask the user if they want to quit
            if not selected:
                message = gui.QMessageBox()
                _ = self.tr
                message.setIcon(message.Question)
                message.setText(_('You did not select any files'))
                message.setInformativeText(_('Did you want to quit?'))
                message.setWindowTitle(_('Did you want to quit?'))
                message.setStandardButtons(message.Yes | message.No)
                message.setDefaultButton(message.Yes)
                answer = message.exec_()

                # yes or application quit
                if answer != message.No: return None
            else:
                filenames += selected

        return filenames


    def __init__(self, arguments):
        'sets the application properties'

        super(Application, self).__init__(arguments)
        self.setApplicationName(self.NAME)


    def exec_(self):
        'starts the application loop and returns the application exit code'

        # unfortunately QApplication needs to look at the arguments so for
        # something like --help we may spin up an application only to close it
        options, filenames = self._parse_arguments(self._get_parser(),
                                                   self.arguments()[1:])

        # if we didn't get all the filenames from the command line let the user
        # add additional files
        count = 2 - len(filenames)
        if count > 0:
            additional = self._prompt_for_files(count)

            # quit
            if additional is None: return 0
            # some other error ?
            elif len(additional) < count: return 1

            filenames += additional

        logger = logging.getLogger(self.NAME)
        logger.debug('starting with files: %r and options: %r' %
                     (filenames, options))

        window = Window(filenames, options)
        window.show()
        super(Application, self).exec_()


if __name__ == '__main__':
    import sys
    app = Application(sys.argv)
    sys.exit(app.exec_())
