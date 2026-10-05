import 'package:project_api_client/api_client.dart';
import 'package:flutter/material.dart';
import '../shared/api/client_provider.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  String _health = '…';

  @override
  void initState() {
    super.initState();
    _check();
  }

  Future<void> _check() async {
    final r = await api.getHealth();
    if (!mounted) return;
    setState(() {
      _health = switch (r) {
        Ok(value: final h) => 'ok (v${h.version})',
        RemoteProblem(problem: final p) => 'error ${p.code}',
        _ => 'unreachable',
      };
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Project')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('API status: $_health'),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () => Navigator.pushNamed(context, '/resources'),
              child: const Text('Resources'),
            ),
          ],
        ),
      ),
    );
  }
}
