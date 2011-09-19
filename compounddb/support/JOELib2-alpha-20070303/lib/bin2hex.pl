o = lo0;     //Zeiger auf die Elemente unterhalb des partitionElement
      int hi = hi0;     //Zeiger auf die Elemente oberhalb des partitionElement
      double pElem;        //partitionElement. It divide the data array in two parts.
      int noRecPar = 20;   //Ist der zu sortierende Teilbereich kleiner als (hier:20) x Elemente, so ueberspringe
                           //die Rekursion. Am Ende aller (mit QuickSort) vorsortierten Elemente wird nun
                           //InsertSoert angewendet. Man koennte auch die einzelnen Teilbereiche mit InsertSort
                           //sortieren, jedoch ist die Anwendung auf das gesamte vorsortierte Array effektiver.

      if ( (hi0 - lo0) >= noRecPar)
      {

         //nimmt einfach das mittlere Element als teilendes Element.
         pElem = xy.x[ ( lo0 + hi0 ) / 2 ];

         //wiederholt die Schleife bis sich die Zeiger schneiden.
         while( lo <= hi )
         {
            //suche das erste Element, das groeSer oder gleich dem teilenden Element (partitionElement)
            //ist, beginnend mit dem kleinsten Index (Zeiger).
            while( ( lo < hi0 ) && ( xy.x[lo] < pElem )) ++lo;

            //suche das erste Element, das kleiner oder gleich dem teilenden Element (partitionElement)
            //ist, beginnend mit dem groeStem Index (Zeiger).
            while( ( hi > lo0 ) && ( xy.x[hi] > pElem )) --hi;

            // vertausche die gefundenen Werte, wenn die Zeiger noch nicht vertauscht sind.
            if( lo <= hi )
            {
               xy.swap(lo, hi);
               ++lo;
               --hi;
            }
         }

         //Wenn