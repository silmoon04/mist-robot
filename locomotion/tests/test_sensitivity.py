import math
import unittest
import importlib.util
from locomotion.sensitivity import plan_cases, score_episode, source_hashes, run_case


def sample(x=0., y=0., yaw=0., time=1., velocity=(.01,0.,0.)):
    return {'position':[x,y,.1],'rpy':[0.,0.,yaw],'body_velocity':list(velocity),
            'body_angular_velocity':[0,0,0],'tracking_error_rad':0.,'torque_saturation_fraction':0.,'nonfoot_ground_contact':False,'time_s':time,'fell':False,'body_ground_contact':False}


class SensitivityTests(unittest.TestCase):
    def test_source_hashes_include_config_and_sources(self):
        hashes=source_hashes()
        self.assertIn('locomotion/config.json',hashes)
        self.assertIn('locomotion/validation_cases.json',hashes)
        self.assertTrue(all(len(v)==64 for v in hashes.values()))

    @unittest.skipUnless(importlib.util.find_spec('pybullet') and importlib.util.find_spec('numpy'), 'simulation dependencies absent')
    def test_tiny_executor_receipt(self):
        case=next(c for c in plan_cases() if c['case_id']=='held-out-heavy-forward')
        result=run_case(case,steps=2)
        self.assertEqual(result['samples'],2)
        self.assertEqual(result['effective_assumptions']['initial_info']['randomization']['scenario'],{'mass_scale':1.25})
        self.assertIn('locomotion/config.json',result['source_hashes'])
        self.assertIn('no_body_ground_contact',result['checks'])

    def test_plan_is_deterministic_and_phone_sensor_valid(self):
        a = plan_cases()
        self.assertEqual(a,plan_cases())
        self.assertEqual(len(a),239)
        self.assertEqual(len({c['case_id'] for c in a}),len(a))
        self.assertEqual(len({c['seed'] for c in a}),len(a))
        for c in a:
            if c['env_kwargs']['sensor_mode'] == 'phone':
                self.assertGreater(c['env_kwargs']['payload'],0)
        self.assertTrue(any('scenario' in c['env_kwargs'] for c in a))

    def test_progress_rotates_initial_body_frame_and_velocity_is_local(self):
        initial=sample(yaw=math.pi/2,time=0.)
        row=sample(y=.192,yaw=math.pi/2,time=19.2)
        result=score_episode(initial,[row],[.01,0,0])
        self.assertTrue(result['passed'])
        self.assertAlmostEqual(result['metrics']['body_velocity_rmse_m_s'],0.)
        self.assertAlmostEqual(result['metrics']['progress_m'],.192)

    def test_stop_bounds_entire_path(self):
        result=score_episode(sample(time=0),[sample(x=.03),sample(time=2)],[0,0,0])
        self.assertFalse(result['checks']['path'])

    def test_missing_contact_evidence_fails(self):
        row=sample(x=.01)
        del row['body_ground_contact']
        self.assertFalse(score_episode(sample(time=0),[row],[.01,0,0])['passed'])

    def test_fall_anywhere_and_minimum_progress(self):
        row=sample(x=.001)
        row['fell']=True
        result=score_episode(sample(time=0),[row,sample(x=.01,time=2)],[.01,0,0])
        self.assertFalse(result['checks']['no_falls'])
        self.assertTrue(result['checks']['progress'])
        with self.assertRaises(ValueError):
            score_episode(sample(time=0),[sample()],[.01,0,0],{'min_progress_fraction':.25})

    def test_yaw_wrap_is_continuous(self):
        result=score_episode(sample(yaw=math.pi-.01,time=0),[sample(yaw=-math.pi+.01)],[0,0,0])
        self.assertAlmostEqual(result['metrics']['peak_yaw_error_rad'],.02)

if __name__=='__main__':
    unittest.main()
