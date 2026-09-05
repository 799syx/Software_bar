import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import app_core as core


class PersonaAvatarTests(unittest.TestCase):
    def test_update_persona_avatar_fields(self):
        core.init_database()
        updated = core.update_persona(
            {
                "avatarPresetKey": "female",
                "avatarId": "test2",
                "refAudio": "data/ref_audio/test2_1.wav",
                "refText": "测试参考文本",
                "avatarVoice": "zh-CN-XiaoyiNeural",
                "ttsMode": "edgetts",
            }
        )
        self.assertEqual(updated["avatarPresetKey"], "female")
        self.assertEqual(updated["avatarId"], "test2")
        self.assertEqual(updated["refAudio"], "data/ref_audio/test2_1.wav")
        self.assertEqual(updated["avatarVoice"], "zh-CN-XiaoyiNeural")

        persona = core.get_persona()
        self.assertEqual(persona["avatarId"], "test2")

        core.update_persona({"avatarPresetKey": "male", "avatarId": "test1"})


if __name__ == "__main__":
    unittest.main()
