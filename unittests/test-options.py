import unittest
from coapy.options import *

class Test_variable_length_integer (unittest.TestCase):
    def test_length_of_vlint (self):
        self.assertEqual(1, length_of_vlint(0))
        self.assertEqual(1, length_of_vlint(255))
        self.assertEqual(2, length_of_vlint(256))
        self.assertEqual(2, length_of_vlint(65535))
        self.assertEqual(3, length_of_vlint(65536))

    def test_pack_vlint (self):
        self.assertEqual('\x00', pack_vlint(0))
        self.assertEqual('\x01', pack_vlint(1))
        self.assertEqual('\x80', pack_vlint(128))
        self.assertEqual('\xff', pack_vlint(255))
        self.assertEqual('\x01\x00', pack_vlint(256))
        self.assertEqual('\xFF\x00', pack_vlint(0xFF00))
        self.assertEqual('\x12\x34\x56', pack_vlint(0x123456))

    def test_unpack_vlint (self):
        self.assertEqual(0, unpack_vlint('\x00'))
        self.assertEqual(1, unpack_vlint('\x01'))
        self.assertEqual(129, unpack_vlint('\x81'))
        self.assertEqual(255, unpack_vlint('\xff'))
        self.assertEqual(0x0110, unpack_vlint('\x01\x10'))
        self.assertEqual(0x123456, unpack_vlint('\x12\x34\x56'))

class TestContentType (unittest.TestCase):
    def test_default (self):
        self.assertEqual(0, ContentType.Default)
        i = ContentType()
        self.assertEqual(ContentType.Default, i.value)
        self.assertEqual('text/plain', i.value_as_string)

    def test_length (self):
        instance = ContentType()
        self.assertEqual(1, instance.length)

    def test_is_critical (self):
        self.assertTrue(ContentType.is_critical())

    def test_ctor (self):
        i = ContentType(2)
        self.assertEqual(2, i.value)
        i = ContentType('text/xml')
        self.assertEqual(1, i.value)

    def assign_value (self, instance, rhs):
        instance.value = rhs

    def assign_value_as_string (self, instance, rhs):
        instance.value_as_string = rhs

    def value_as_string (self, instance):
        return instance.value_as_string

    def test_mutator (self):
        i = ContentType()
        self.assertTrue(i.is_default())
        i.value = 0
        self.assertEqual(0, i.value)
        self.assertEqual('text/plain', i.value_as_string)
        i.value_as_string = 'text/csv'
        self.assertEqual(2, i.value)
        self.assertFalse(i.is_default())

        # OK to assign an undefined integer value as long as it's in range,
        # but you can't see it as a string
        i.value = 6
        self.assertEqual(6, i.value)
        self.assertRaises(KeyError, self.value_as_string, i)

        self.assertRaises(ValueError, self.assign_value, i, -1)
        self.assertRaises(ValueError, self.assign_value, i, 'no/media')
        self.assertRaises(ValueError, self.assign_value, i, 256)
        self.assertRaises(TypeError, self.assign_value, i, None)

        # Not OK to assign an undefined string value
        self.assertRaises(ValueError, self.assign_value_as_string, i, 'no/media')
        
class TestMaxAge (unittest.TestCase):
    def test_is_critical (self):
        self.assertFalse(MaxAge.is_critical())

    def assign_value (self, instance, value):
        instance.value = value

    def test_default (self):
        self.assertEqual(60, MaxAge.Default)
        i = MaxAge()
        self.assertEqual(MaxAge.Default, i.value)
        self.assertEqual(1, i.length)

    def test_value (self):
        i = MaxAge()
        i.value = 0
        self.assertEqual(0, i.value)
        self.assertEqual(1, i.length)
        p = i.packed
        self.assertEqual('\x00', p)
        
        i.value = 64
        self.assertEqual(64, i.value)
        self.assertEqual(1, i.length)
        i.value = 256
        self.assertEqual(256, i.value)
        self.assertEqual(2, i.length)
        self.assertRaises(TypeError, self.assign_value, i, None)
        i.value = '34'
        self.assertEqual(34, i.value)
        v = (1 << 32) - 1
        i.value = v
        self.assertEqual(v, i.value)
        self.assertEqual(4, i.length)
        v += 1
        self.assertRaises(ValueError, self.assign_value, i, v)

class TestEtag (unittest.TestCase):
    def testLengthLimits (self):
        self.assertRaises(ValueError, Etag, '')
        i = Etag('1')
        self.assertEqual('1', i.value)
        self.assertEqual(1, i.length)
        i = Etag('1234')
        self.assertEqual('1234', i.value)
        self.assertEqual(4, i.length)
        self.assertRaises(ValueError, Etag, '12345')

class TestLocation (unittest.TestCase):
    def assign_value (self, instance, value):
        instance.value = value

    def test_ctor (self):
        self.assertRaises(ValueError, Location)
        i = Location('1')
        self.assertEqual('1', i.value)
        self.assertRaises(ValueError, Location, '/')

class TestUriPath (unittest.TestCase):
    def test_default (self):
        self.assertEqual('', UriPath.Default)
        i = UriPath()
        self.assertEqual(UriPath.Default, i.value)
        self.assertEqual(0, i.length)
        self.assertTrue(i.is_default())

    def assign_value (self, instance, value):
        instance.value = value

    def test_value (self):
        i = UriPath()
        i.value = '.well-known/r'
        self.assertEqual('.well-known/r', i.value)
        self.assertEqual(13, i.length)
        self.assertFalse(i.is_default())
        i.value = ''
        self.assertEqual(UriPath.Default, i.value)
        self.assertEqual(0, i.length)
        self.assertTrue(i.is_default())
        self.assertRaises(ValueError, self.assign_value, i, '/')
        self.assertRaises(ValueError, self.assign_value, i, '/.well-known/r')

class TestEncode (unittest.TestCase):
    def testEmpty (self):
        self.assertEqual((0, ''), encode([]))

    def testLengthExtension (self):
        MAX_OPTION_LENGTH = 270

        uri_path = UriPath('1')
        self.assertEqual((1, '\x911'), encode([ uri_path ]))
        uri_path.value = '123456789abcd'
        self.assertEqual((1, '\x9d123456789abcd'), encode([ uri_path ]))
        uri_path.value = '123456789abcde'
        self.assertEqual((1, '\x9e123456789abcde'), encode([ uri_path ]))
        uri_path.value = '123456789abcdef'
        self.assertEqual((1, '\x9f\x00123456789abcdef'), encode([ uri_path ]))
        uri_path.value = ' ' * MAX_OPTION_LENGTH
        (num_options, packed) = encode([ uri_path ])
        self.assertEqual(1, num_options)
        self.assertEqual(272, len(packed))
        self.assertTrue(packed.startswith('\x9f\xff'))
        # Note: bypass length validation
        uri_path._value = ' ' * (1 + MAX_OPTION_LENGTH)
        self.assertRaises(Exception, encode, [uri_path])

    def testInteger (self):
        max_age = MaxAge(0x1b)
        self.assertEqual((1, '\x21\x1b'), encode([ max_age ]))

    def testContentType (self):
        content_type = ContentType('video/raw')
        self.assertEqual((1, '\x11\x1a'), encode([ content_type ]))

    def testIgnoredDefaults (self):
        self.assertEqual((0, ''), encode([ UriPath() ]))

    def testMultiple (self):
        options = set()
        options.add(UriPath('s')) # 9
        options.add(MaxAge(30)) # 2
        options.add(ContentType('application/link-format')) # 1 val 40
        (num_options, packed) = encode(options)
        self.assertEqual(3, num_options)
        self.assertEqual('\x11\x28\x11\x1e\x71\x73', packed)

class TestDecode (unittest.TestCase):
    def testEmpty (self):
        packed = 'any string'
        ( options, remainder ) = decode(0, packed)
        self.assertEqual(0, len(options))
        self.assertEqual(remainder, packed)

    def testLengthExtension (self):
        uri_path = UriPath('1')
        (_, packed) = encode([ uri_path ])
        payload = 'payload'
        packed += payload
        (options, remainder) = decode(1, packed)
        self.assertEqual(1, len(options))
        opt = options.pop()
        self.assertTrue(isinstance(opt, UriPath))
        self.assertEqual(opt.value, uri_path.value)
        self.assertEqual(remainder, payload)

    def testInteger (self):
        max_age = MaxAge(0x1b)
        (_, packed) = encode([ max_age ])
        payload = 'payload'
        packed += payload
        (options, remainder) = decode(1, packed)
        self.assertEqual(1, len(options))
        opt = options.pop()
        self.assertTrue(isinstance(opt, MaxAge))
        self.assertEqual(opt.value, max_age.value)
        self.assertEqual(remainder, payload)

    def testContentType (self):
        content_type = ContentType('video/raw')
        (_, packed) = encode([ content_type ])
        payload = 'payload'
        packed += payload
        (options, remainder) = decode(1, packed)
        self.assertEqual(1, len(options))
        opt = options.pop()
        self.assertTrue(isinstance(opt, ContentType))
        self.assertEqual(opt.value, content_type.value)
        self.assertEqual(remainder, payload)

    def testUnrecognizedElective (self):
        options = '\xa2AB'
        payload = 'payload'
        packed = options + payload
        (options, remainder) = decode(1, packed)
        self.assertEqual(0, len(options))
        self.assertEqual(remainder, payload)

    def testUnrecognizedCritical (self):
        options = '\xb2AB'
        payload = 'payload'
        packed = options + payload
        self.assertRaises(Exception, decode, 1, packed)

    def testMultiple (self):
        packed = '\x11\x28\x11\x1e\x71\x73'
        payload = 'something'
        (options, remainder) = decode(3, packed + payload)
        self.assertEqual(3, len(options))
        self.assertEqual(remainder, payload)
        option_list = sorted(options, lambda _a,_b: cmp(_a.Type, _b.Type))
        opt = option_list.pop(0)
        self.assertTrue(isinstance(opt, ContentType))
        self.assertEqual('application/link-format', opt.value_as_string)
        opt = option_list.pop(0)
        self.assertTrue(isinstance(opt, MaxAge))
        self.assertEqual(30, opt.value)
        opt = option_list.pop(0)
        self.assertTrue(isinstance(opt, UriPath))
        self.assertEqual('s', opt.value)

class TestBlock (unittest.TestCase):
    def test_ctor (self):
        i = Block(0, True, 7)
        self.assertEqual(0x0b, i.value)
        i = Block(1, True, 7)
        self.assertEqual(0x1b, i.value)
        
class TestRegistry (unittest.TestCase):
    def testRegistry (self):
        self.assertEqual(8, len(Registry))

if __name__ == '__main__':
    unittest.main()
    
