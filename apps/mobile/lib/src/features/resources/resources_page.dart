import 'package:project_api_client/api_client.dart';
import 'package:flutter/material.dart';
import '../../shared/api/client_provider.dart';
import '../../shared/api/error_copy.dart';

class ItemVM {
  final String id;
  final String name;
  final bool locked;
  const ItemVM({required this.id, required this.name, required this.locked});
}

ItemVM toVM(Resource dto) => ItemVM(id: dto.id, name: dto.name, locked: dto.locked);

class ResourcesPage extends StatefulWidget {
  const ResourcesPage({super.key});

  @override
  State<ResourcesPage> createState() => _ResourcesPageState();
}

class _ResourcesPageState extends State<ResourcesPage> {
  List<ItemVM> _items = [];
  String _error = '';

  @override
  void initState() {
    super.initState();
    _reload();
  }

  Future<void> _reload() async {
    final r = await api.listResources();
    if (!mounted) return;
    setState(() {
      switch (r) {
        case Ok(value: final list):
          _items = list.items.map(toVM).toList();
          _error = '';
        case RemoteProblem(problem: final p):
          _error = errorCopy(p.code);
        case Cancelled():
          break;
        case TransportFailure(message: final m):
        case ProtocolFailure(message: final m):
          _error = m;
      }
    });
  }

  Future<void> _delete(String id) async {
    final r = await api.deleteResource(id);
    if (!mounted) return;
    switch (r) {
      case Ok():
        _reload();
      case RemoteProblem(problem: final p):
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(errorCopy(p.code))));
        }
      default:
        break;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Resources')),
      body: _error.isNotEmpty && _items.isEmpty
          ? Center(child: Text(_error))
          : ListView.builder(
              itemCount: _items.length,
              itemBuilder: (context, i) {
                final it = _items[i];
                return ListTile(
                  title: Text(it.name),
                  trailing: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (it.locked) const Text('🔒'),
                      IconButton(
                        icon: const Icon(Icons.delete),
                        onPressed: () => _delete(it.id),
                      ),
                    ],
                  ),
                );
              },
            ),
      floatingActionButton: FloatingActionButton(
        onPressed: _reload,
        child: const Icon(Icons.refresh),
      ),
    );
  }
}
