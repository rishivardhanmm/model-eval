
import struct
import unittest

from message_adapter import send_message, decode_messages


class MessageAdapterTests(unittest.TestCase):

    def test_ascii_message(self):
        frame = send_message("hello")
        declared_length = struct.unpack(">I", frame[:4])[0]

        self.assertEqual(declared_length, 5)
        self.assertEqual(frame[4:], b"hello")

    def test_accented_message(self):
        frame = send_message("café")
        declared_length = struct.unpack(">I", frame[:4])[0]

        self.assertEqual(declared_length, len("café".encode("utf-8")))

    def test_emoji_message(self):
        frame = send_message("hi 😀")
        declared_length = struct.unpack(">I", frame[:4])[0]

        self.assertEqual(declared_length, len("hi 😀".encode("utf-8")))

    def test_two_consecutive_messages(self):
        first = "café"
        second = "hi 😀"
        stream = send_message(first) + send_message(second)

        messages, consumed = decode_messages(stream)

        self.assertEqual(messages, [first, second])
        self.assertEqual(consumed, len(stream))

    def test_empty_message(self):
        frame = send_message("")
        messages, consumed = decode_messages(frame)

        self.assertEqual(messages, [""])
        self.assertEqual(consumed, len(frame))

    def test_truncated_frame_is_rejected(self):
        with self.assertRaises(ValueError):
            decode_messages(b"\x00\x00\x00\x05hi")

    def test_print_verification_report(self):
        messages = ["hello", "café", "hi 😀"]
        frames = [send_message(message) for message in messages]
        stream = b"".join(frames)

        print("\n--- Message Adapter Verification ---")

        for message, frame in zip(messages, frames):
            declared_length = struct.unpack(">I", frame[:4])[0]
            payload = frame[4:]

            print(f"\nMessage: {message!r}")
            print(f"Declared length: {declared_length}")
            print(f"Actual payload bytes: {len(payload)}")
            print(f"Payload: {payload!r}")

            self.assertEqual(declared_length, len(payload))

        decoded, consumed = decode_messages(stream)

        print(f"\nDecoded messages: {decoded}")
        print(f"Bytes consumed: {consumed}/{len(stream)}")

        self.assertEqual(decoded, messages)
        self.assertEqual(consumed, len(stream))


if __name__ == "__main__":
    unittest.main(verbosity=2)
