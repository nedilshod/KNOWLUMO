"""Focused regression tests for caption timing and mathematical visual cues."""
import unittest
import render

class Captions(unittest.TestCase):
 def test_alignment_matches_script(self):
  for i,(tokens,_) in enumerate(render.CAPTION_DATA):
   self.assertEqual(len(tokens),len(render.ALIGN[i]))
   self.assertEqual([t.rstrip('.,!?;:').lower() for t in tokens],
     [w['word'].split('(')[0].lower() for w in render.ALIGN[i]])
 def test_never_shows_future_words(self):
  for i,scene in enumerate(render.ALIGN):
   for j,word in enumerate(scene):
    group,active=render.caption_state(i,word['start']+.001)
    self.assertGreaterEqual(active,j)
    visible=[idx for idx,_ in group if idx<=active]
    self.assertTrue(all(scene[idx]['start']<=word['start']+.001 for idx in visible))
 def test_hold_through_real_pauses(self):
  for i,scene in enumerate(render.ALIGN):
   for j in range(len(scene)-1):
    if scene[j]['end']<scene[j+1]['start']:
     t=(scene[j]['end']+scene[j+1]['start'])/2
     group,active=render.caption_state(i,t)
     self.assertEqual(active,j)
     self.assertIn(j,[idx for idx,_ in group])
 def test_hold_across_scene_boundary(self):
  self.assertIsNone(render.caption_state(0,0))
  for i in range(1,len(render.ALIGN)):
   group,active=render.caption_state(i,0)
   if render.ALIGN[i][0]['start']>0:
    self.assertEqual(active,len(render.ALIGN[i-1])-1)
   else:
    self.assertEqual(active,0)
 def test_30fps(self): self.assertEqual(render.FPS,30)

if __name__=='__main__': unittest.main()
