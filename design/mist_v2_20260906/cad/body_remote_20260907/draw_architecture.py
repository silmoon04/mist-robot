"""Engineering topology sketches; no body-packaging fit is implied."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Circle

OUT=Path(__file__).resolve().parent
fig,axs=plt.subplots(2,2,figsize=(16,10),facecolor='#fafaf7')
ink='#263238';blue='#00798c';orange='#b56822';purple='#69569b';gray='#56666e'
for ax in axs.flat:
    ax.set(xlim=(0,100),ylim=(0,100));ax.axis('off');ax.set_facecolor('#fafaf7')
def box(ax,x,y,w,h,text,color=ink,dashed=False):
    ax.add_patch(Rectangle((x,y),w,h,fill=False,edgecolor=color,linewidth=1.6,linestyle='--' if dashed else '-'))
    ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=11,color=color,linespacing=1.45)
def arrow(ax,a,b,color=ink):
    ax.annotate('',xy=b,xytext=a,arrowprops=dict(arrowstyle='->',lw=1.6,color=color))
def title(ax,text):ax.text(0,97,text,fontsize=16,fontweight='bold',color=ink,va='top')

ax=axs[0,0];title(ax,'A. Strict chassis-fixed, independent feeds')
box(ax,2,53,25,27,'Three body-fixed\nH / K / W motors')
box(ax,36,53,25,27,'Three independent\nfirst-axis pickups',blue)
box(ax,70,53,28,27,'Hip outputs\nh, h+k, h+k+w')
arrow(ax,(27,67),(36,67));arrow(ax,(61,67),(70,67))
ax.text(49,46,'Carrier-relative pickup: beta = alpha - q0',ha='center',fontsize=12,color=blue)
ax.text(2,35,'Each motor must also compensate first-axis motion.',fontsize=11,color=ink)
ax.text(2,26,'Ideal yaw effort can become (tau0 - tauH) / r0.',fontsize=11,color=ink)
ax.text(2,17,'Three colored shafts need real, separately supported gears.',fontsize=11,color=ink)
ax.text(2,8,'Published spatial differential is a different strict-fixed option.',fontsize=11,color=gray)

ax=axs[0,1];title(ax,'D. Enclosed joint plate + fixed wheel motor')
box(ax,2,53,27,28,'H / K motors\non internal plate',dashed=True)
box(ax,39,53,27,28,'Physical pitch\ndifferential',blue)
box(ax,77,53,21,28,'Femur +\nknee outputs')
arrow(ax,(29,67),(39,67));arrow(ax,(66,67),(77,67))
box(ax,2,19,27,20,'Chassis-fixed\nwheel motor',purple)
box(ax,39,19,27,20,'One first-axis\nwheel pickup',purple)
box(ax,77,19,21,20,'Continuous\nwheel feed',purple)
arrow(ax,(29,29),(39,29),purple);arrow(ax,(66,29),(77,29),purple)
ax.text(2,8,'The complete moving plate must stay inside the body at every pose.',fontsize=11,color=ink)

ax=axs[1,0];title(ax,'Nested K / W shaft: possible support order')
# Radial cross-section is drawn to the stated shaft diameters.
section=ax.inset_axes([.02,.31,.38,.42])
section.set(xlim=(-4.4,4.4),ylim=(-4.4,4.4));section.set_aspect('equal');section.axis('off')
section.add_patch(Circle((0,0),4,facecolor='#b9d9dd',edgecolor=blue,lw=2))
section.add_patch(Circle((0,0),3,facecolor='#fafaf7',edgecolor=blue,lw=1.3))
section.add_patch(Circle((0,0),2.5,facecolor='#cfcae4',edgecolor=purple,lw=1.5))
ax.text(21,23,'Radial section',ha='center',fontsize=11,color=gray)
ax.text(47,72,'K: steel tube OD8 / ID6 mm',fontsize=12,color=blue)
ax.text(47,60,'W: independent 5 mm core',fontsize=12,color=purple)
ax.text(47,48,'Nominal radial gap: 0.5 mm',fontsize=11,color=ink)
ax.text(47,36,'608 supports tube; external 685',fontsize=11,color=ink)
ax.text(47,27,'stations can support the core.',fontsize=11,color=ink)
ax.text(2,12,'End bearings cost axial length. An outer-tube cross-pin would hit the core.',fontsize=10.5,color=ink)
ax.text(2,3,'Fits, hub locks, bending and fatigue remain manufacturing checks.',fontsize=10.5,color=gray)

ax=axs[1,1];title(ax,'Wheel route beyond the hip')
for x,label in ((10,'HIP'),(49,'KNEE'),(89,'WHEEL')):
    ax.text(x,84,label,ha='center',fontsize=11,color=ink)
    ax.add_patch(Circle((x,66),5,fill=False,edgecolor=blue,lw=1.6))
ax.plot([10,49],[71,71],color=blue,lw=2);ax.plot([10,49],[61,61],color=blue,lw=2)
ax.plot([10,49],[56,56],color=purple,lw=2)
ax.plot([49,89],[71,71],color=purple,lw=2);ax.plot([49,89],[61,61],color=purple,lw=2)
ax.text(27,76,'K belt',fontsize=10,color=blue,ha='center')
ax.text(27,48,'W belt',fontsize=10,color=purple,ha='center')
ax.text(69,76,'W belt',fontsize=10,color=purple,ha='center')
ax.text(50,37,'All-belt route needs K, W-in and W-out pulley bands at knee.',ha='center',fontsize=10.5,color=ink)
ax.text(2,23,'Alternative: knee miter -> supported tibia shaft -> wheel miter.',fontsize=10.5,color=orange)
ax.text(2,13,'Narrower shin trades pulley bands for four gears and thrust bearings.',fontsize=10.5,color=ink)
ax.text(2,3,'Carrier phase remains: incoming wheel angle = h + k + w.',fontsize=10.5,color=gray)

fig.suptitle('All actuators inside the body: power paths and tradeoffs',x=.04,y=.985,ha='left',fontsize=22,color=ink)
fig.text(.04,.014,'Topology study only. Motor stations, joint envelopes and full swept body clearance are not yet fitted.  |  7 September 2026',fontsize=10,color=gray)
fig.subplots_adjust(left=.035,right=.985,bottom=.06,top=.925,wspace=.1,hspace=.13)
fig.savefig(OUT/'architecture_routes.svg',facecolor=fig.get_facecolor())
fig.savefig(OUT/'architecture_routes.png',dpi=150,facecolor=fig.get_facecolor())
plt.close(fig)
print(OUT/'architecture_routes.png')
