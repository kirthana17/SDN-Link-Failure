
from mininet.topo import Topo

class TriangleTopo(Topo):
    def build(self):
        h1 = self.addHost('h1', ip='10.0.0.1/24')
        h2 = self.addHost('h2', ip='10.0.0.2/24')

        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')

        self.addLink(h1, s1)
        self.addLink(h2, s3)

        self.addLink(s1, s2)
        self.addLink(s2, s3)
        self.addLink(s1, s3)

topos = {'triangle': TriangleTopo}
