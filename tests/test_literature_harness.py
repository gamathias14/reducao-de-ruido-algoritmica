from __future__ import annotations

import unittest

import numpy as np

from benchmark_audio.literature_harness import (
    BASELINE_SYSTEM_ID,
    DeepFilterNetAdapter,
    FrozenBaselineAdapter,
    OMLSAIMCRAAdapter,
    RNNoiseAdapter,
    WebRTCAPMNSAdapter,
    audio_sha256,
    canonical_roundtrip,
    planned_systems,
)


class LiteratureHarnessTests(unittest.TestCase):
    def test_registry_plan_has_unique_system_ids(self) -> None:
        systems = planned_systems()
        ids = [system.system_id for system in systems]

        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids[0], BASELINE_SYSTEM_ID)
        self.assertTrue(systems[0].available)
        self.assertTrue(systems[1].available)
        self.assertFalse(systems[-1].available)

    def test_baseline_is_exactly_checkpoint46r_e0_s02(self) -> None:
        adapter = FrozenBaselineAdapter()

        self.assertEqual(adapter.config.noise_quantile, 0.22)
        self.assertEqual(adapter.config.low_energy_alpha, 0.30)
        self.assertEqual(adapter.config.spectral_floor, 0.02)
        self.assertEqual(adapter.config.gain_smoothing, 0.0)
        self.assertEqual(adapter.metadata.api_frame_samples, 320)
        self.assertEqual(adapter.metadata.analysis_hop_samples, 160)

    def test_audio_hash_is_stable_for_float32_little_endian(self) -> None:
        audio = np.asarray([0.0, 0.5, -0.5], dtype=np.float64)

        first = audio_sha256(audio)
        second = audio_sha256(audio.astype(np.float32))

        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)

    def test_resampling_roundtrip_preserves_shape_and_finiteness(self) -> None:
        rng = np.random.default_rng(3527)
        audio = rng.normal(scale=0.05, size=3_201).astype(np.float32)

        restored = canonical_roundtrip(audio, native_sample_rate=48_000)

        self.assertEqual(restored.shape, audio.shape)
        self.assertTrue(np.all(np.isfinite(restored)))

    def test_baseline_adapter_preserves_shape_and_is_deterministic(self) -> None:
        rng = np.random.default_rng(3527)
        noisy = rng.normal(scale=0.05, size=3_200).astype(np.float32)
        adapter = FrozenBaselineAdapter()

        first = adapter.process(noisy, 16_000)
        second = adapter.process(noisy, 16_000)

        self.assertEqual(first.audio.shape, noisy.shape)
        self.assertTrue(np.array_equal(first.audio, second.audio))
        self.assertGreater(first.state_memory_bytes or 0, 0)

    def test_omlsa_imcra_adapter_preserves_shape(self) -> None:
        rng = np.random.default_rng(3527)
        noisy = rng.normal(scale=0.05, size=3_200).astype(np.float32)
        adapter = OMLSAIMCRAAdapter()

        result = adapter.process(noisy, 16_000)

        self.assertEqual(result.audio.shape, noisy.shape)
        self.assertTrue(np.all(np.isfinite(result.audio)))
        self.assertGreater(result.processing_seconds, 0.0)

    def test_rnnoise_metadata_is_pinned(self) -> None:
        metadata = RNNoiseAdapter().metadata

        self.assertEqual(metadata.native_sample_rate, 48_000)
        self.assertEqual(metadata.api_frame_samples, 480)
        self.assertEqual(metadata.algorithmic_latency_ms, 20.0)
        self.assertEqual(
            metadata.source_revision,
            "904a876dce1f9ab8860c0a5000ed151f9f6eef58",
        )

    def test_rnnoise_impulse_is_aligned_when_binary_is_available(self) -> None:
        adapter = RNNoiseAdapter()
        if not adapter.metadata.available:
            self.skipTest("Binario RNNoise nao compilado.")
        audio = np.zeros(4_800, dtype=np.float32)
        audio[1_000] = 0.5

        result = adapter.process(audio, 48_000)
        peak = int(np.argmax(np.abs(result.audio)))

        self.assertLessEqual(abs(peak - 1_000), 3)
        self.assertEqual(result.diagnostics["alignment_trim_samples"], 480)

    def test_webrtc_apm_metadata_is_pinned(self) -> None:
        metadata = WebRTCAPMNSAdapter().metadata

        self.assertEqual(metadata.native_sample_rate, 16_000)
        self.assertEqual(metadata.api_frame_samples, 160)
        self.assertEqual(metadata.analysis_window_samples, 256)
        self.assertEqual(metadata.lookahead_samples, 96)
        self.assertEqual(metadata.algorithmic_latency_ms, 6.0)
        self.assertEqual(
            metadata.source_revision,
            "eb79ac6e330baa0a6d26c53d522f9ed57495edb7",
        )

    def test_webrtc_apm_impulse_is_aligned_when_binary_is_available(self) -> None:
        adapter = WebRTCAPMNSAdapter()
        if not adapter.metadata.available:
            self.skipTest("Binario WebRTC APM nao compilado.")
        audio = np.zeros(4_800, dtype=np.float32)
        audio[1_600] = 0.5

        result = adapter.process(audio, 16_000)
        peak = int(np.argmax(np.abs(result.audio)))

        self.assertEqual(result.audio.shape, audio.shape)
        self.assertLessEqual(abs(peak - 1_600), 1)
        self.assertEqual(result.diagnostics["alignment_trim_samples"], 96)

    def test_deepfilternet_metadata_is_pinned(self) -> None:
        metadata = DeepFilterNetAdapter().metadata

        self.assertEqual(metadata.native_sample_rate, 48_000)
        self.assertEqual(metadata.analysis_window_samples, 960)
        self.assertEqual(metadata.analysis_hop_samples, 480)
        self.assertEqual(metadata.lookahead_samples, 1_440)
        self.assertEqual(metadata.algorithmic_latency_ms, 30.0)
        self.assertEqual(
            metadata.source_revision,
            "978576aa8400552a4ce9730838c635aa30db5e61",
        )

    def test_deepfilternet_impulse_is_aligned_when_available(self) -> None:
        adapter = DeepFilterNetAdapter()
        if not adapter.metadata.available:
            self.skipTest("Ambiente DeepFilterNet nao instalado.")
        audio = np.zeros(24_000, dtype=np.float32)
        audio[12_000] = 0.5

        result = adapter.process(audio, 48_000)
        peak = int(np.argmax(np.abs(result.audio)))

        self.assertEqual(result.audio.shape, audio.shape)
        self.assertLessEqual(abs(peak - 12_000), 2)
        self.assertEqual(result.diagnostics["alignment_trim_samples"], 1_440)


if __name__ == "__main__":
    unittest.main()
