<pre>
        volumeMounts:
        - name: sense-rm-vol
          mountPath: /opt/config
      volumes:
        - name: sense-rm-vol
          persistentVolumeClaim:
            claimName: sense-rm-vol
            
            
        volumeMounts:
        - name: sense-agent01-vol
          mountPath: /opt/config
      volumes:
        - name: sense-agent01-vol
          persistentVolumeClaim:
            claimName: sense-agent01-vol
</pre>
