# encoding: utf-8

from twisted.internet import reactor
from twisted.web import server
from twisted.python import log
from twisted.web.resource import Resource

from hathor.p2p.peer_id import PeerId
from hathor.p2p.resources import StatusResource, MiningResource, TransactionResource
from hathor.p2p.factory import HathorFactory
from hathor.transaction.storage import TransactionJSONStorage, TransactionMemoryStorage
from hathor.wallet.resources import BalanceResource, HistoryResource, AddressResource, SendTokensResource
import hathor

import argparse
import sys
import json


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--hostname', help='Hostname used to be accessed by other peers')
    parser.add_argument('--testnet', action='store_true', help='Connect to Hathor testnet')
    parser.add_argument('--dns', action='append', help='Seed DNS')
    parser.add_argument('--peer', help='json file with peer info')
    parser.add_argument('--listen', action='append', help='Address to listen for new connections (eg: tcp:8000)')
    parser.add_argument('--bootstrap', action='append', help='Address to connect to (eg: tcp:127.0.0.1:8000')
    parser.add_argument('--status', type=int, help='Port to run status server')
    parser.add_argument('--data', help='Data directory')
    args = parser.parse_args()

    log.startLogging(sys.stdout)

    if not args.peer:
        peer_id = PeerId()
    else:
        data = json.load(open(args.peer, 'r'))
        peer_id = PeerId.create_from_json(data)

    print('Hathor v{}'.format(hathor.__version__))
    print('My peer id is', peer_id.id)

    if args.data:
        tx_storage = TransactionJSONStorage(path=args.data)
        print('Using TransactionJSONStorage at {}'.format(args.data))
    else:
        tx_storage = TransactionMemoryStorage()
        print('Using TransactionMemoryStorage')

    network = 'testnet'
    factory = HathorFactory(peer_id=peer_id, network=network, hostname=args.hostname, tx_storage=tx_storage)

    if args.testnet:
        factory.dns_seed_lookup_text('testnet.hathor.network')

    if args.dns:
        for host in args.dns:
            factory.dns_seed_lookup(host)

    if args.listen:
        for description in args.listen:
            factory.listen(description)

    if args.bootstrap:
        for description in args.bootstrap:
            factory.connect_to(description)

    if args.status:
        # TODO get this from a file. How should we do with the factory?
        root = Resource()
        wallet_resource = Resource()
        root.putChild(b'wallet', wallet_resource)

        resources = (
            (b'status', StatusResource(factory), root),
            (b'mining', MiningResource(factory), root),
            (b'transaction', TransactionResource(factory), root),
            (b'balance', BalanceResource(factory), wallet_resource),
            (b'history', HistoryResource(factory), wallet_resource),
            (b'address', AddressResource(factory), wallet_resource),
            (b'send_tokens', SendTokensResource(factory), wallet_resource),
        )
        for url_path, resource, parent in resources:
            parent.putChild(url_path, resource)

        status_server = server.Site(root)
        reactor.listenTCP(args.status, status_server)

    reactor.run()
