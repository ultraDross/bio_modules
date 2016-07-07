import unittest 
from get_seq.UCSC import *


class TestNormal(unittest.TestCase):
    ''' Test all methods in UCSC.py under the default
        arguments
        ### HAVE MULTIPLE WITH OTHER VALUES FOR ARGUMENTS, SO NOT ONLY DEFAULT VALUES ARE TESTED

    '''
    Test = ScrapeSeq("Test", 20, 20, "hg19", "Y")
    var_pos = "15:48762884"

    def test_region(self):
        self.assertEqual(TestNormal.Test.create_region(TestNormal.var_pos),
                         "15:48762864,48762904")

    def test_region_info(self):
        self.assertEqual(TestNormal.Test.get_region_info("15:48762864,48762904"),
                                'agcctatctcacactcacagCggaacaggccagggaggttg')

    def test_header(self):
        self.assertEqual(TestNormal.Test.header_option(
            "Test", TestNormal.var_pos, "15:48762864,48762904",
            'agcctatctcacactcacagCggaacaggccagggaggttg'),
            '> Test 15:48762884 15:48762864,48762904')


class TestErrorHandeling(unittest.TestCase):
    ''' Ensure custom exceptions work as anticipated
    '''
    def test_all_exceptions(self):
        ''' Ensure custom exceptions are raised upon parsing 
            invlaid arguments
        '''
        with self.assertRaises(WrongHGversion):
            ScrapeSeq("Test", 20, 20, "hg1", "Y").handle_argument_exception(
            "15:48762864")
        with self.assertRaises(TypographyError):
            ScrapeSeq("Test", 20, 20, "hg19", "Y").handle_argument_exception(
                "151671617")
        with self.assertRaises(TypographyError):
            ScrapeSeq("Test", 20, 20, "hg19", "Y").handle_argument_exception(
                "15::1671617,")
        with self.assertRaises(TypographyError):
            ScrapeSeq("Test", 20, 20, "hg19", "Y").handle_argument_exception(
                "15:1671617,,1671680")
        with self.assertRaises(TypographyError):
            ScrapeSeq("Test", 20, 20, "hg19", "Y").handle_argument_exception(
                "15:1671--617")

if __name__ == '__main__':
    unittest.main()
