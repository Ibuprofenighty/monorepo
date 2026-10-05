import 'package:flutter/material.dart';
import 'pages/home_page.dart';
import 'features/resources/resources_page.dart';

/// App shell. API wiring lives in shared/api; pages stay thin.
class ProjectApp extends StatelessWidget {
  const ProjectApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Project',
      theme: ThemeData(colorSchemeSeed: Colors.indigo, useMaterial3: true),
      routes: {
        '/': (_) => const HomePage(),
        '/resources': (_) => const ResourcesPage(),
      },
    );
  }
}
