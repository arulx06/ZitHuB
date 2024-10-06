import hashlib

class MerkleTree:
    def _init_(self, data_blocks):
        self.data_blocks = data_blocks
        self.leaf_nodes = [self.hash_data(block) for block in data_blocks]
        self.root = self.build_tree(self.leaf_nodes)

    def hash_data(self, data):
        """Hashes the data block."""
        return hashlib.sha256(data.encode()).hexdigest()

    def build_tree(self, nodes):
        """Builds the Merkle Tree and returns the root hash."""
        if len(nodes) == 1:
            return nodes[0]  # Only one node means it's the root

        # If the number of nodes is odd, duplicate the last node
        if len(nodes) % 2 != 0:
            nodes.append(nodes[-1])

        # Create new level of nodes
        parent_nodes = []
        for i in range(0, len(nodes), 2):
            parent_nodes.append(self.hash_pair(nodes[i], nodes[i + 1]))

        # Recursive call to build the next level
        return self.build_tree(parent_nodes)

    def hash_pair(self, left, right):
        """Hashes a pair of nodes."""
        return hashlib.sha256((left + right).encode()).hexdigest()

    def get_root(self):
        """Returns the Merkle Root."""
        return self.root