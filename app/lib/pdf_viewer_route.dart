import 'dart:io';
import 'package:flutter/material.dart';
import 'package:syncfusion_flutter_pdfviewer/pdfviewer.dart';

class PdfViewerRoute extends StatelessWidget {
  const PdfViewerRoute({super.key, required this.pdfPath});

  final String pdfPath;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
        appBar: AppBar(
          title: const Text('PDF Viewer'),
        ),
        body: SfPdfViewer.file(File(pdfPath)));
  }
}
