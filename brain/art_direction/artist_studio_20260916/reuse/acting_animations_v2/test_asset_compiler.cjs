'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const {splitFeatures,metrics,imageDifference,separateByComponents,equalVisibleRgba,registerFrames,normalizeTransparentRgb,appearanceHash}=require('./build_assets.cjs');

function rect(raw,width,x,y,w,h,alpha=255) {
  for(let yy=y;yy<y+h;yy++)for(let xx=x;xx<x+w;xx++){
    const p=(yy*width+xx)*4;raw[p]=54;raw[p+1]=229;raw[p+2]=227;raw[p+3]=alpha;
  }
}

test('shared transparent bands separate both eyes and mouth',()=>{
  const width=120,height=100;
  const frames=Array.from({length:12},(_,i)=>{
    const raw=Buffer.alloc(width*height*4);
    rect(raw,width,20,20,25,i===3?2:20);rect(raw,width,75,20,25,i===3?2:20);rect(raw,width,48,76,24,5);return raw;
  });
  const splits=splitFeatures(frames,width,height);
  assert(splits.horizontalBand[0]>39&&splits.horizontalBand[1]<76);
  assert(splits.centralGap[0]>44&&splits.centralGap[1]<75);
  assert.equal(metrics(frames[3],width,height,splits.rects.leftEye).visiblePixels,50);
  assert.equal(metrics(frames[0],width,height,splits.rects.mouth).visiblePixels,120);
  assert.equal(imageDifference(frames[0],frames[0],width,height).alphaDifferencePerVisiblePixel,0);
});

test('rectangular detection rejects visible artwork crossing either split',()=>{
  const width=120,height=100,raw=Buffer.alloc(width*height*4);
  rect(raw,width,20,20,25,20);rect(raw,width,75,20,25,20);rect(raw,width,48,76,24,5);
  const joinedEyes=Buffer.from(raw);rect(joinedEyes,width,45,20,30,20);
  assert.throws(()=>splitFeatures([joinedEyes],width,height),/central gap/);
  const joinedMouth=Buffer.from(raw);rect(joinedMouth,width,50,30,8,55);
  assert.throws(()=>splitFeatures([joinedMouth],width,height),/horizontal band/);
});

test('overlapping bounds use disjoint component masks with exact visible RGBA reconstruction',()=>{
  const width=110,height=100,raw=Buffer.alloc(width*height*4);
  // Hidden RGB is deliberately nonzero; only alpha-bearing source pixels matter visually.
  for(let p=0;p<raw.length;p+=4){raw[p]=8;raw[p+1]=16;raw[p+2]=32;}
  rect(raw,width,20,20,20,22);rect(raw,width,70,20,20,22);
  rect(raw,width,47,39,8,21);rect(raw,width,37,50,28,10);
  rect(raw,width,45,40,1,1,1);rect(raw,width,26,18,1,1,3);
  const original=Buffer.from(raw);
  assert.throws(()=>splitFeatures([raw],width,height),/horizontal band/);
  const separated=separateByComponents(raw,width,height);
  assert.deepEqual(raw,original,'separation must never mutate source artwork');
  const reconstructed=Buffer.alloc(raw.length),masks=Object.values(separated.masks);
  for(let p=0;p<raw.length;p+=4){
    const contributors=masks.filter(mask=>mask[p+3]);
    assert.equal(contributors.length,raw[p+3]?1:0,'each alpha-bearing source pixel belongs to exactly one layer');
    if(contributors.length)contributors[0].copy(reconstructed,p,p,p+4);
  }
  assert(equalVisibleRgba(raw,reconstructed));
  assert.equal(metrics(separated.masks.leftEye,width,height).visiblePixels,440);
  assert.equal(metrics(separated.masks.rightEye,width,height).visiblePixels,440);
  assert.equal(separated.masks.mouth[(40*width+47)*4+3],255);
  assert.equal(separated.masks.leftEye[(40*width+39)*4+3],255);
  assert.equal(separated.masks.mouth[(40*width+39)*4+3],0,'overlapping bounds must not duplicate eye pixels in mouth');
});

test('registration preserves blink descent and changes only whole-face placement',()=>{
  const width=120,height=100;
  const source=Array.from({length:12},(_,i)=>{
    const raw=Buffer.alloc(width*height*4),drift=i%3;
    rect(raw,width,20+drift,20+drift,25,i===3?2:20);rect(raw,width,75+drift,20+drift,25,i===3?2:20);rect(raw,width,48+drift,76+drift,24,5);return raw;
  });
  const registered=registerFrames(source,width,height);
  const mouthCenters=registered.raws.map(raw=>{
    const split=splitFeatures([raw],registered.width,registered.height);
    return metrics(raw,registered.width,registered.height,split.rects.mouth).centroid;
  });
  assert(mouthCenters.every(c=>Math.abs(c[0]-mouthCenters[0][0])<=1&&Math.abs(c[1]-mouthCenters[0][1])<=1));
  assert(registered.width>=width&&registered.height>=height);
  assert.equal(registered.raws[3].filter((_,i)=>i%4===3&&registered.raws[3][i]===255).length,220);
});

test('display optimization changes RGB only at exactly zero alpha',()=>{
  const raw=Buffer.from([19,55,200,0, 55,98,162,1, 100,159,201,7, 70,200,240,128, 61,255,222,255]);
  const original=Buffer.from(raw),result=normalizeTransparentRgb(raw);
  assert.deepEqual(raw,original,'source buffer remains immutable');
  assert.deepEqual(result.raw.subarray(0,4),Buffer.from([0,0,0,0]));
  assert.deepEqual(result.raw.subarray(4),raw.subarray(4),'alpha1 and all visible RGB/alpha values remain exact');
  assert.equal(result.pixelsCleared,1);
  assert(equalVisibleRgba(raw,result.raw));
  assert.equal(appearanceHash(raw),appearanceHash(result.raw));
});
