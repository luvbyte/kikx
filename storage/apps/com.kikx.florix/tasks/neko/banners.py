from neko.lib.ui import Pre, Text, Animate

B1 = Animate(Pre(Text(r"""
♡  /)/)
 （„• ֊ •„)♡              
┏ • UU • - • - • - • - • - • - • ღ❦ღ┓
                 <span class="text-blue-300 font-bold">NEKO</span> 
            created by <span class="text-red-300">kikx</span>
┗ღ❦ღ • - • - • - • - • - • - • - •  ┛
     \(•.•)/              \(•.•)/
       | |                  | |
      _/ \_                _/ \_
/````````````````````````````````````\
""")))
B1.add_class("w-full h-full flex items-end justify-center")

B2 = Animate(Pre(Text(r"""
  /)/) E            K (\(\
 (•.•)/              \(•.•)
N/| |                  | |\O
 _/ \_                _/ \_
""")), "slideInUp")
B2.add_class("w-full h-full flex items-end justify-center")

B3 = Animate(Pre(Text(r"""
(`“ •.  (`“•.¸🌼¸.•“´)  ¸. •“´)
    🌸«•🍃   NEKO  🍃•“»🌸
(¸. • “´(¸.•“´🌼 `“•)` “° •.¸)
""")), "rubberBand")
B3.add_class("w-full h-full flex items-center justify-center")


BANNERS = [B1, B2, B3]

